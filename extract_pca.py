''' Reads survey_results.json and writes pca_results.json '''

import numpy as np
import pandas as pd
import json
import re
from scipy.linalg import eig
import matplotlib.pyplot as plt


def pca(X):
    ''' Principal Components Analysis '''
    cov_matrix = np.cov(X.T)
    evals, evecs = eig(cov_matrix)
    idcs = np.argsort(evals)[::-1]
    evecs = evecs.real[:, idcs]
    evals = evals.real[idcs]

    return evecs, evals


def preprocess(df):

    old_vals = ['Strongly Disagree',
                'Disagree',
                'Uncertain',
                'Agree',
                'Strongly Agree',
                'No Opinion',
                'Did Not Answer',
                None]
    new_vals = [-1.5,
                -1,
                0,
                1,
                1.5,
                np.nan,
                np.nan,
                np.nan]

    df = df.replace(old_vals, new_vals)

    # Only retain responders with > 75% response rate
    num_questions = len(df.columns)

    df = df[df.count(axis=1) > (num_questions * 0.75)]

    # Replace remaining nans with the column mean
    df = df.fillna(df.mean())

    return df


def main():

    # Read data extracted
    df = pd.read_json("survey_results.json")

    # Separate url suffixes from column names
    q_url_suffixes = list(df.ix['q_url_suffix', :])[:-1]
    df = df.drop('q_url_suffix')

    # Separate responder IDs from row names
    df = preprocess(df)
    responder_id = df['responder_id']
    del df['responder_id']

    # Compute +/- 2SD for each question *before* mean-centering.
    X = np.array(df)
    igm_top_range = X.mean(axis=0) + 2 * X.std(axis=0)
    igm_bot_range = X.mean(axis=0) - 2 * X.std(axis=0)

    # Center data across columns. For PCA.
    X = X - np.reshape(X.mean(axis=1), (-1, 1))

    # Run PCA and compute 2D projection
    evecs, evals = pca(X)
    evecs = -evecs  # so that physically left is politically left
    proj = np.dot(X, evecs[:, 0:2])

    # Get correlation matrix
    pc1_order = np.argsort(proj[:, 0])
    corr_mat = np.corrcoef(X[pc1_order, :])

    # User info dict
    user_info = {'name': 'You',
                 'x': 0,
                 'y': 0,
                 'responder_id': 0}

    # List of responder info dicts, including user dict
    points = [user_info]
    for i in range(len(proj)):
        responder_info = {'name': df.index[i],
                          'x': proj[i, 0],
                          'y': proj[i, 1],
                          'responder_id': str(responder_id[i]),
                          'pc1_order': int(np.argwhere(pc1_order == i))}
        points.append(responder_info)

    out = {}
    out['points'] = points
    out['q_url_suffixes'] = q_url_suffixes
    out['questions'] = [re.sub(r"\(0+", "(", col) for col in df.columns]
    out['xweights'] = list(evecs[:, 0])
    out['yweights'] = list(evecs[:, 1])
    out['X'] = [['%.2f' % el for el in row] for row in X.tolist()]
    out['corr_mat'] = [['%.2f' % el for el in row]
                       for row in corr_mat.tolist()]
    out['igm_top_range'] = ['%.2f' % el for el in igm_top_range]
    out['igm_bot_range'] = ['%.2f' % el for el in igm_bot_range]

    for idx in np.argsort(out['xweights']).tolist():
        print(out['questions'][idx] + "\n")

    print(len(X))

    # Write to file
    f = open("pca_results.json", "w")
    json.dump(out, f, indent=2)
    f.close()

    # Plot responders in 2D space
    plt.figure()
    plt.scatter(proj[:, 0], proj[:, 1])
    plt.show()

if __name__ == "__main__":
    main()

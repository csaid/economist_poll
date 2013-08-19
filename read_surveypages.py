''' Grabs all IGM data from their websites and saves to survey_results.json '''

import urllib2
import re
from unidecode import unidecode
from pandas import DataFrame, Series


def clean_string(s):
    ''' Remove junk characters from question string'''
    s = re.sub(r"[\t]", "", s)
    s = re.sub(r"[\n]", " ", s)
    s = re.sub(r"<[\s\S]*?>", "", s)
    s = re.sub(r"&nbsp;", " ", s)
    s = re.sub(r"<.*?>", "", s)
    s = ' '.join(s.split())

    return s

def get_page_contents(url):
    ''' Load contents of a question page. May contain sub-questions'''
    page = urllib2.urlopen(url)
    encoding = page.headers['content-type'].split('charset=')[-1]
    contents = unidecode(unicode(page.read(), encoding))
    page.close()

    return contents




def main():

    # Get links to survey pages
    home_url = "http://www.igmchicago.org/igm-economic-experts-panel"
    home_contents = get_page_contents(home_url)
    urls = re.findall(r"<h2><a href=\"(\S+?results\?SurveyID=\S+?)\"", home_contents)
    urls = ["http://www.igmchicago.org" + url for url in urls]


    # Loop through survey pages
    df = DataFrame()
    question_count = 0
    for url in urls:

        contents = get_page_contents(url)

        questions = re.findall(r"surveyQuestion\">([\s\S]+?)</h3>", contents)
        responder_list = re.findall(r"\?id=([\d]+)?\">([\s\w.]+?)</a>", contents)

        responses = re.findall(r"<span class=\"option-[\d]+?\">([\s\w.]+?)</span>", contents)
        num_responders = len(responses)/len(questions)

        # Loop through sub-questions (A, B, etc) within each page
        for i, question in enumerate(questions):
            question = clean_string(question)
            question_count += 1
            print(question)

            # Restrict range to responses for this sub-question
            rng = (i*num_responders, (i+1)*num_responders)

            # Collect sub-question, its url suffix, and the responses
            prefix = "(%03d" % question_count + ") "
            q_responses = Series(responses[rng[0]:rng[1]], index=responder_list[rng[0]:rng[1]])
            q_url_suffix = re.findall("=(.+)", url)[0]
            q_responses = q_responses.append(Series([q_url_suffix], index=['q_url_suffix']))
            q_responses.name = prefix+question.strip()

            # Add question data to dataframe
            df = df.join(q_responses, how='outer')


    # Move responder id from index to column, only after all joins are complete
    df['responder_id'] = [pair[0] for pair in df.index]
    df.index = [pair[1] if type(pair)==tuple else pair for pair in df.index]

    # Write to file
    df.to_json("survey_results.json")


if __name__ == "__main__":
    main()

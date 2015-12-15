''' Grabs all IGM data from their websites and saves to survey_results.json '''

import urllib2
import re
from unidecode import unidecode
from pandas import DataFrame, Series
from bs4 import BeautifulSoup

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


# Get links to survey pages
home_url = "http://www.igmchicago.org/igm-economic-experts-panel"
home_contents = get_page_contents(home_url)
home_soup = BeautifulSoup(home_contents)
meta = DataFrame()
meta['url'] = ["http://www.igmchicago.org" + qtag.a.get('href') for qtag in home_soup.find_all("h2")]
meta['year'] = [int(tag.text.split(',')[2].split(' ')[1]) for tag in home_soup.find_all("h6")]
meta.ix[meta['year'] < 2013, 'year'] = 2013 # Count any question prior to 2013 as 2013


for year in [2015]:

    df = DataFrame()
    question_count = 0
    urls = meta.query('year == @year')['url'].values

    for url in reversed(urls):


        soup = BeautifulSoup(get_page_contents(url))
        year = soup.h6.contents[0].split(',')[2].split(' ')[1]

        questions = [qtag.text for qtag in soup.find_all("h3", class_="surveyQuestion")]

        response_tags = soup.find_all('tr', class_="parent-row")
        responses, responders = [],[]
        for response_tag in response_tags:
            responder = (response_tag.a.get("href").split('=')[1], clean_string(response_tag.a.text))
            response = clean_string(response_tag.span.text)
            responders.append(responder)
            responses.append(response)


        num_responders = len(responses) / len(questions)

        # Loop through sub-questions (A, B, etc) within each page
        for i, question in enumerate(questions):

            # Clean out extraneous text from question.
            question = clean_string(question)
            comment_idx = question.find('The experts panel previously voted')
            if comment_idx >= 0:
                question = question[0 : comment_idx - 1]

            question_count += 1
            print(question)

            # Restrict range to responses for this sub-question
            rng = (i * num_responders, (i + 1) * num_responders)

            # Collect sub-question, its url suffix, and the responses
            prefix = "(%03d" % question_count + ") "
            q_responses = Series(
                responses[rng[0]:rng[1]], index=responders[rng[0]:rng[1]])
            q_url_suffix = re.findall("=(.+)", url)[0]
            q_responses = q_responses.append(
                Series([q_url_suffix], index=['q_url_suffix']))
            q_responses.name = prefix + question.strip()

            # Add question data to dataframe
            df = df.join(q_responses, how='outer')


    # Move responder id from index to column, only after all joins are complete
    df['responder_id'] = [pair[0] for pair in df.index]
    df.index = [pair[1] if type(pair) == tuple else pair for pair in df.index]

    # Write to file
    df.to_json("survey_results_" + str(year) + ".json")





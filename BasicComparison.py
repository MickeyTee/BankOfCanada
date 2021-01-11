from flask import Flask, request
import requests
import pandas as pd


def get_BOC_data(series, start_date, end_date):
    """
    Gets the observations from the specified series from the Bank of Canada valet service in the date range specified,
    containing the observations level of the JSON object.
    :param series: A string containing the Bank of Canada code for the series to be retrieved.
    :param start_date: A string with the first date we will return in YYYY-MM-DD format
    :param end_date: A string with the last date we will return in YYYY-MM-DD format
    :return: A dataframe containing the data series
    """
    # Specify the base URL
    base_url = "https://www.bankofcanada.ca/valet/"
    # Specify the route for the series we want
    route = "observations/" + series + "?start_date=" + start_date + "&end_date=" + end_date

    # Request the data
    req = requests.get(base_url + route)
    # Decode the json from the request into a python dictionary
    data = req.json()
    # Get the observations into a dataframe
    series_frame = pd.json_normalize(data['observations'])
    # For convenience and consistency purposes, let's rename the columns
    series_frame.columns = ['dates', 'values']
    # Cast the two columns before returning
    series_frame['dates'] = series_frame['dates'].astype(str)
    series_frame['values'] = series_frame['values'].astype(float)

    return series_frame


def overlap_frames(df1, df2):
    """
    Takes two dataframes and merges them, creating two separate series within the dataframe corresponding to the
    overlapping dates.
    :param df1: A dataframe containing two columns, one series of dates and one series of values
    :param df2: A dataframe just like the first
    :return: A single dataframe containing both the previous
    """

    # Merge the two dataframes
    merged = pd.merge(left=df1, right=df2, how='outer', left_on='dates', right_on='dates')

    # Create two additional columns with the values from the series when both dates are present
    merged['overlap_x'] = merged[merged['values_x'].notnull() & merged['values_y'].notnull()]['values_x']
    merged['overlap_y'] = merged[merged['values_x'].notnull() & merged['values_y'].notnull()]['values_y']

    # Sort by date, just in case.
    merged.sort_values(by='dates')

    return merged


def calc_pearson(df):
    """
    Takes a dataframe with two columns which have been created with overlap_frames() and calculates the pearson
    coefficient of correlation if it is possible to do so, otherwise returns 999.
    Note that the method has been left deliberately basic to demonstrate the mathematics of calculating pearson
    correlation.
    :param df: A dataframe built with overlap_frames()
    :return: a float containing the pearson coefficient of correlation between list1 and list2
    """

    series1 = df[df['overlap_x'].notnull()]['overlap_x']
    series2 = df[df['overlap_y'].notnull()]['overlap_y']

    # Can't calculate pearson correlation on uneven lengths of series, and a series with 1 or 0 values zero variance
    if len(series1) != len(series2) or len(series1) <= 1 or len(series2) <= 1:
        # Display a nonsensical value that the user will know is NOT a pearson correlation
        corr = 999
    # Otherwise the length must be the same and the lists must have at least two values
    else:
        # Store the length to make the code easier on the eyeballs
        length = len(series1)

        # Begin by getting the mean of each series by dividing the sum of the values by the length of the list
        mean1 = series1.sum() / length
        mean2 = series2.sum() / length

        # Get the series of differences
        diff1 = series1 - mean1
        diff2 = series2 - mean2

        # Get the average of the squared differences for both series
        var1 = (diff1 * diff1).sum() / length
        var2 = (diff2 * diff2).sum() / length
        # Get the average of the product of the two series of differences
        cov = (diff1 * diff2).sum() / length

        # Take the square root of the variance to get standard deviation
        st_dev1 = var1 ** 0.5
        st_dev2 = var2 ** 0.5

        # Make sure we're not about to divide by zero
        if st_dev1 == 0 or st_dev2 == 0:
            corr = 999
        # Otherwise, calculate correlation
        else:
            corr = cov / (st_dev1 * st_dev2)

    return corr


def create_table(df):
    """
    Creates a list of lists that we'll use to populate an HTML template using a dataframe built with overlap_frames().
    :param df: a Dataframe built with overlap_frames
    :return:
    """
    # A placeholder list that we will populate that will contain our table rows
    table = []
    # Get the column names to iterate over
    column_names = ['values_x', 'values_y', 'overlap_x', 'overlap_y']

    # Create some lists that will represent the table rows and label them
    min_val = ['Low']
    min_date = ['Low occurred on:']
    max_val = ['High']
    max_date = ['High occurred on:']
    mean_val = ['Mean:']
    corr = ['Pearson Correlation:', '', '', '']

    # Iterate over the column names we've supplied (except Pearson)
    for i in column_names:
        # Append the minimum value from each column
        min_val.append(df[i].min())
        # Append the corresponding date to that minimum value; get only the first value
        min_date.append(df[df[i] == df[i].min()]['dates'].values[0])

        # Append the maximum value from each column to the appropriate row
        max_val.append(df[i].max())
        # Append the corresponding date to that maximum value; get only the first value
        max_date.append(df[df[i] == df[i].max()]['dates'].values[0])

        # Append the mean rounded to four decimal places
        mean_val.append(round(df[i].mean(), 4))

    # Calculate pearson for the overlapping dates rounded to four decimal places
    corr[3] = round(calc_pearson(df), 4)

    # Append all the lists corresponding to rows to table
    for i in [min_val, min_date, max_val, max_date, mean_val, corr]:
        table.append(i)

    return table


def date_ranges(series1, series2):
    """
    Gets the date ranges from two dataframes and returns them in a list of strings
    :param series1: A dataframe containing a 'dates' column
    :param series2: Another dataframe containing another 'dates' column
    :return: A list of four dates
    """
    # Create an empty list we'll populate
    date_list = []

    # Iterate over both series
    for series in (series1, series2):
        date_list.append(series['dates'].min())
        date_list.append(series['dates'].max())

    return date_list





app = Flask(__name__)


@app.route('/')
def index():
    # Render the basic template, passing a few parameters to get started


if __name__ == '__main__':
    app.run()

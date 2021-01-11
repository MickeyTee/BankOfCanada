from flask import Flask, request, jsonify
import requests
import pandas as pd
import json
import datetime


def get_BOC_data(series, start_date, end_date):
    """
    Gets the observations from the specified series from the Bank of Canada valet service in the date range specified,
    containing the observations level of the JSON object. Technically this allows for dates that do not exist (e.g. Feb
    31st), but
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
    series_df = pd.json_normalize(data['observations'])
    # For convenience and consistency purposes, let's rename the columns
    series_df.columns = ['dates', 'values']
    # Cast the two columns before returning
    series_df['dates'] = series_df['dates'].astype(str)
    series_df['values'] = series_df['values'].astype(float)

    return series_df


def check_date(date):
    """
    Checks two dates in string format to see if they are in the realm of plausibility by making sure the fields are of
    the correct length and don't have values that could never be valid.
    :param date: A date in YYYY-MM-DD format stored as a string
    :return: A boolean indicating if the dates meet the required format
    """

    # Create a flag to return which we will try to falsify
    flag = True
    # Use a try block in case the input is not in the format specified or too short
    try:
        # Try to convert the date provided to a datetime, which will ensure only valid date inputs return true
        datetime.datetime(int(date[:4]), int(date[5:7]), int(date[8:10]))
    # If any of the int conversions fail, we must not have a valid date, so set flag = False
    except:
        flag = False

    return flag


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

    return merged


def calc_pearson(df):
    """
    Takes a dataframe with two columns which have been created with overlap_frames() and calculates the Pearson
    coefficient of correlation if it is possible to do so, otherwise returns 999.
    Note that the method has been left deliberately basic to demonstrate the mathematics of calculating Pearson
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


app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    # Create a placeholder dictionary to populate
    response = {'message': 'Please double check the dates to ensure they are valid.',
                'FXUSDCAD': {'low': 0, 'high': 0, 'mean': 0, 'mindate': '0000-00-00', 'maxdate': '0000-00-00'},
                'AVG.INTWO': {'low': 0, 'high': 0, 'mean': 0, 'mindate': '0000-00-00', 'maxdate': '0000-00-00'},
                'rho': 999}
    global current_data1
    global current_data2
    # Just in case the request is empty, prevent a None request from crashing the server
    try:
        # Convert the JSON formatted byte string to a dictionary
        request_dict = json.loads(request.data)
    except:
        # Create a generic start date and end date
        request_dict = {'startDate': '', 'endDate': ''}

    # Get the start and end dates
    start_date = request_dict['startDate']
    end_date = request_dict['endDate']

    # Check if the date sent by the GUI is after the last date stored in memory
    if (end_date > current_data1['dates'].max()):
        # Change the start date so that we don't unnecessarily request additional data
        data_start_date = current_data1['dates'].max()

    # Ensure our dates are valid and that the start date is before the end date
    if check_date(start_date) and check_date(end_date) and start_date <= end_date:
        try:

            # Call the bank of Canada API with the dates sent from the GUI
            df_FX_USDCAD = get_BOC_data('FXUSDCAD', data_start_date, end_date)
            df_AVG_INTWO = get_BOC_data('AVG.INTWO', data_start_date, end_date)

            # Append the data
            current_data1 = current_data1.append(df_FX_USDCAD[1:])
            current_data2 = current_data2.append(df_AVG_INTWO[1:])

            # Create some indices to slice the dataframes over
            min_date_index_1 = 0
            min_date_index_2 = 0
            max_date_index_1 = len(current_data1)
            max_date_index_2 = len(current_data2)

            # Assign the indices
            if start_date <= current_data1['dates'].min():
                min_date_index_1 = 0
            else:
                min_date_index_1 = current_data1.index[current_data1['dates'] == start_date][0]

            if start_date <= current_data2['dates'].min():
                min_date_index_2 = 0
            else:
                min_date_index_2 = current_data2.index[current_data2['dates'] == start_date][0]
            
            if end_date <= current_data2['dates'].max():
                max_date_index_1 = len(current_data1)
            elif end_date >= '2020-10-27':
                max_date_index_1 = len(current_data1)
            else:
                max_date_index_1 = current_data2.index[current_data1['dates'] == end_date][0]

            if end_date <= current_data2['dates'].max():
                max_date_index_2 = len(current_data2)
            elif end_date >= '2020-10-27':
                max_date_index_2 = len(current_data2)
            else:
                max_date_index_2 = current_data2.index[current_data2['dates'] == end_date][0]

            
            # Get the high values
            response['FXUSDCAD']['high'] = current_data1['values'][min_date_index_1:max_date_index_1].max()
            response['AVG.INTWO']['high'] = current_data2['values'][min_date_index_2:max_date_index_2].max()

            # Get the low values
            response['FXUSDCAD']['low'] = current_data1['values'][min_date_index_1:max_date_index_1].min()
            response['AVG.INTWO']['low'] = current_data2['values'][min_date_index_2:max_date_index_2].min()
            # Get the mean values, rounding to  4 decimal places for readability
            response['FXUSDCAD']['mean'] = round(current_data1['values'][min_date_index_1:max_date_index_1].mean(), 4)
            response['AVG.INTWO']['mean'] = round(current_data2['values'][min_date_index_2:max_date_index_2].mean(), 4)
            # Get the first date that appears
            response['FXUSDCAD']['mindate'] = current_data1['dates'][min_date_index_1:max_date_index_1].min()
            response['AVG.INTWO']['mindate'] = current_data2['dates'][min_date_index_2:max_date_index_2].min()
            # Get the last date that appears
            response['FXUSDCAD']['maxdate'] = current_data1['dates'][min_date_index_1:max_date_index_1].max()
            response['AVG.INTWO']['maxdate'] = current_data2['dates'][min_date_index_2:max_date_index_2].max()

            # Calculate the "overlapped frame"
            df_FX_CORRA = overlap_frames(current_data1[min_date_index_1:max_date_index_1], current_data2[min_date_index_2:max_date_index_2])
            # Calculate the Pearson coefficient of correlation, rounding to 4 decimal places again
            response['rho'] = round(calc_pearson(df_FX_CORRA), 4)
            # Update the message with a little feedback about correlation
            response['message'] = 'Note that correlation is calculated for the overlapping time period only.'

        except:
            print("EXCEPTION")
            # Update the message with a little feedback about the failure
            response['message'] = 'Something went wrong in retrieving data. Double check the date format.'

    print(response)
    # Convert the dictionary to JSON
    response = jsonify(response)
    # Allow any origin, which we can do relatively safely since this app will only ever run locally
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


if __name__ == '__main__':


    # On server start-up (however many days or months ago) make an API call to get the most up to date data
    try:
        # Call the bank of Canada API with the dates sent from the GUI
        current_data1 = get_BOC_data('FXUSDCAD', '2017-01-03', '2020-06-30')
        current_data2 = get_BOC_data('AVG.INTWO', '2017-01-03', '2020-06-30')
    except:
        pass

    app.run()


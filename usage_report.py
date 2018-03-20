import datetime
import os
import time

import requests
import simplejson

from datadog import initialize, api

"""
This script can be installed as a cron job to retrieve usage metrics.
We recommend running no more frequently than every 15 minutes.
Metrics API is currently in Beta and metrics are delayed by 48 hours.
Example cron entry:
*/15 * * * * /usr/bin/python /home/username/dd_usage_report/usage_report.py
"""

DD_API_KEY = os.environ.get('DD_API_KEY')
DD_APP_KEY = os.environ.get('DD_APP_KEY')

options = {
    'api_key': DD_API_KEY,
    'app_key': DD_APP_KEY
}

initialize(**options)

# Retrieving usage message via requests

USAGE_URL = 'https://app.datadoghq.com/api/v1/usage/'
DD_KEYS = '?api_key=' + DD_API_KEY + '&application_key=' + DD_APP_KEY

def format_standard_metrics(metrics, start_hr):
    metric_list = []
    for metric_dict in metrics:
        try:
            for k, v in metric_dict.iteritems():
                if k == 'hour':
                    if v != start_hr:
                        print('Incorrect hour for metrics. Aborting metric submission.')
                        return
                else:
                    metric_name = 'datadog.usage.' + k
                    metric_list.append({'metric': metric_name, 'points': v})
        except AttributeError:
            print('Metrics are not in dict format')
    return metric_list

def format_toplist_metrics(metrics):
    metric_list = []
    for metric_dict in metrics:
        try:
            metric_name_tag = 'metric_name:' + metric_dict['metric_name']
            avg_metric = {
                'metric': 'datadog.usage.top_metrics_avg_hour',
                'points': metric_dict['avg_metric_hour'],
                'tags': [metric_name_tag]
            }
            metric_list.append(avg_metric)
            max_metric = {
                'metric': 'datadog.usage.top_metrics_max_hour',
                'points': metric_dict['max_metric_hour'],
                'tags': [metric_name_tag]
            }
            metric_list.append(max_metric)
        except AttributeError:
            print('Metrics are not in dict format')
    return metric_list

def get_usage_metrics(url):
    usage_metrics = []
    try:
        usage_metrics = requests.get(url).json().get('usage', None)
    except requests.exceptions.MissingSchema:
        print('Invalid URL format: {}'.format(url))
    except requests.exceptions.ConnectionError:
        print('Could not connect to url: {}'.format(url))
    except simplejson.scanner.JSONDecodeError:
        print('The response did not contain JSON data')
    return usage_metrics

def build_standard_url(endpoint):
    # Example date format for hour: 2018-03-14T09
    start = datetime.datetime.now() - datetime.timedelta(hours=48)
    start_hr = start.strftime('%Y-%m-%dT%H')
    end = datetime.datetime.now() - datetime.timedelta(hours=47)
    end_hr = end.strftime('%Y-%m-%dT%H')
    url = USAGE_URL + endpoint + DD_KEYS + '&start_hr=' + start_hr + '&end_hr=' + end_hr
    return url, start_hr

def update_standard_metrics(endpoint):
    # Build url
    url, start_hr = build_standard_url(endpoint)
    # Get usage metrics from Datadog
    metrics = get_usage_metrics(url)
    # Convert metrics to format for submitting
    metrics_list = format_standard_metrics(metrics, start_hr)
    # Submit metrics
    if len(metrics_list):
        submit_metrics(metrics_list)
    else:
        print('No usage metrics available for endpiont: {}'.format(endpoint))

def update_toplist_metrics():
    now = datetime.datetime.now()
    url = USAGE_URL + 'top_avg_metrics' + DD_KEYS + '&month=' + now.strftime('%Y-%m')
    metrics = get_usage_metrics(url)
    metrics_list = format_toplist_metrics(metrics)
    # Submit metrics
    if len(metrics_list):  # TODO: Move this logic
        submit_metrics(metrics_list)
    else:
        print('No toplist usage metrics available')

def submit_metrics(metric_list):
    api.Metric.send(metric_list)

# It looks like this data is processed from the previous day only.  So there must be a job that is running nightly to create these metrics.  We should just pull 24 hours behind by default.

class MainClass(object):

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def main(self):
        # host data
        update_standard_metrics('hosts')
        # hourly usage data
        update_standard_metrics('timeseries')
        #top metrics
        update_toplist_metrics()

MainClass().main()

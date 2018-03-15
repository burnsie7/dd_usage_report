import datetime
import os
import time

import requests
import simplejson

from datadog import initialize, api

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

def format_standard_metrics, start_hr):
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

def submit_metrics(metric_list):
    api.Metric.send(metric_list)

def update_standard_metrics(endpoint):
    # Example date format for hour: 2018-03-14T09
    start = datetime.datetime.now() - datetime.timedelta(hours=24)
    start_hr = start.strftime('%Y-%m-%dT%H')
    end = datetime.datetime.now() - datetime.timedelta(hours=23)
    end_hr = end.strftime('%Y-%m-%dT%H')
    url = USAGE_URL + 'hosts' + DD_KEYS + '&start_hr=' + start_hr + '&end_hr=' + end_hr

    # Get usage metrics from Datadog
    metrics = get_usage_metrics(url)
    # Convert metrics to format for submitting
    metrics_list = format_standard_metrics(metrics, start_hr)
    # Submit metrics
    submit_metrics(metrics_list)

def update_toplist_metrics():
    now = datetime.datetime.now()
    url = USAGE_URL + 'top_avg_metrics' + DD_KEYS + '&month=' + now.strftime('%Y-%m')
    metrics = get_usage_metrics(url)
    metrics_list = format_toplist_metrics(metrics)
    # Submit metrics
    submit_metrics(metrics_list)

# It looks like this data is processed from the previous day only.  So there must be a job that is running nightly to create these metrics.  We should just pull 24 hours behind by default.

# host data
update_standard_metrics('hosts')

# hourly usage data
update_standard_metrics('timeseries')

#top metrics
update_toplist_metrics()

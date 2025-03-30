import sys
import multiprocessing
import ssl
import socket
import datetime
import concurrent.futures
import math

DEFAULT_HTTPS_PORT = 443
WORKER_THREAD_COUNT = multiprocessing.cpu_count()
SOCKET_CONNECTION_TIMEOUT_SECONDS = 10
WARN_IF_DAYS_LESS_THAN = 7
EXIT_SUCCESS = 0
EXIT_EXPIRING_SOON = 1
EXIT_ERROR = 2
EXIT_NO_HOST_LIST = 9

def make_host_port_pair(endpoint):
    host, port, id = endpoint.split(':')
    port = int(port or DEFAULT_HTTPS_PORT)  # Default to HTTPS port if not specified
    return host, port, int(id)

def pluralise(singular, count):
    return '{} {}{}'.format(count, singular, '' if count == 1 else 's')

def get_certificate_expiry_date_time(context, host, port):
    try:
        with socket.create_connection((host, port), SOCKET_CONNECTION_TIMEOUT_SECONDS) as tcp_socket:
            with context.wrap_socket(tcp_socket, server_hostname=host) as ssl_socket:
                # certificate_info is a dict with lots of information about the certificate
                certificate_info = ssl_socket.getpeercert()
                exp_date_text = certificate_info['notAfter']
                return datetime.datetime.fromtimestamp(ssl.cert_time_to_seconds(exp_date_text), datetime.timezone.utc)
    except Exception as e:
        #raise RuntimeError(f"Failed to retrieve certificate for {host}:{port} - {e}")
        return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=101)


def format_time_remaining(time_remaining):
    day_count = time_remaining.days

    if day_count >= WARN_IF_DAYS_LESS_THAN:
        return pluralise('day', day_count)

    else:
        seconds_per_minute = 60
        seconds_per_hour = seconds_per_minute * 60
        seconds_unaccounted_for = time_remaining.seconds

        hours = int(seconds_unaccounted_for / seconds_per_hour)
        seconds_unaccounted_for -= hours * seconds_per_hour

        minutes = int(seconds_unaccounted_for / seconds_per_minute)

        return '{} {} {}'.format(
            pluralise('day', day_count),
            pluralise('hour', hours),
            pluralise('min', minutes)
        )

def get_exit_code(err_count, min_days):
    code = EXIT_SUCCESS

    if err_count:
        code += EXIT_ERROR

    if min_days < WARN_IF_DAYS_LESS_THAN:
        code += EXIT_EXPIRING_SOON

    return code

def format_host_port(host, port):
    return host + ('' if port == DEFAULT_HTTPS_PORT else ':{}'.format(port))

def check_certificates(endpoints):
    context = ssl.create_default_context()
    host_port_pairs = [make_host_port_pair(endpoint) for endpoint in endpoints]

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKER_THREAD_COUNT) as executor:
        futures = {
            executor.submit(get_certificate_expiry_date_time, context, host, port):
            (host, port, id) for host, port, id in host_port_pairs
        }

        endpoint_count = len(endpoints)
        err_count = 0
        min_days = math.inf
        max_host_port_len = max([len(format_host_port(host, port)) for host, port, _ in host_port_pairs])
        for future in concurrent.futures.as_completed(futures):
            host, port, id = futures[future]
            try:
                expiry_time = future.result()
            except Exception as ex:
                err_count += 1
                print('{} ERROR {}'.format(format_host_port(host, port).ljust(max_host_port_len), ex))
            else:
                time_remaining = expiry_time - datetime.datetime.now(datetime.timezone.utc)
                time_remaining_txt = format_time_remaining(time_remaining)
                days_remaining = time_remaining.days
                min_days = min(min_days, days_remaining)

                print('{} {:<5} expires in {}'.format(
                    format_host_port(host, port).ljust(max_host_port_len),
                    'WARN' if days_remaining < WARN_IF_DAYS_LESS_THAN else 'OK',
                    time_remaining_txt))

def get_certificates_data(endpoints):
    out_list = []
    context = ssl.create_default_context()
    host_port_pairs = [make_host_port_pair(endpoint) for endpoint in endpoints]

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKER_THREAD_COUNT) as executor:
        futures = {
            executor.submit(get_certificate_expiry_date_time, context, host, port):
            (host, port, id) for host, port, id in host_port_pairs
        }

        for future in concurrent.futures.as_completed(futures):
            host, port, id = futures[future]
            try:
                expiry_time = future.result()
            except Exception as ex:
                print('{} ERROR {}'.format(format_host_port(host, port), ex))
            else:
                time_remaining = expiry_time - datetime.datetime.now(datetime.timezone.utc)
                days_remaining = time_remaining.days

                record = {
                    "id": id,
                    "host": host,
                    "port": str(port),
                    "expiry_time": str(expiry_time),
                    "days_remaining": days_remaining
                }
                out_list.append(record)
    return out_list

if __name__ == '__main__':
    endpoints = sys.argv[1:]

    if len(endpoints):
        records = check_certificates(endpoints)
        print(records)
    else:
        endpoints = ['www.google.com:443:1']
        records = check_certificates(endpoints)
        print(records)
        
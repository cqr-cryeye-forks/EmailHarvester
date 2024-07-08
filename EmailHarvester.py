#!/usr/bin/env python3
# encoding: UTF-8

"""
    This file is part of EmailHarvester
    Copyright (C) 2016 @maldevel
    https://github.com/maldevel/EmailHarvester

    EmailHarvester - A tool to retrieve Domain email addresses from Search Engines.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    For more see the file 'LICENSE' for copying permission.
"""

__author__ = "maldevel"
__copyright__ = "Copyright (c) 2016 @maldevel"
__credits__ = ["maldevel", "PaulSec", "cclauss", "Christian Martorella"]
__license__ = "GPLv3"
__version__ = "1.3.2"
__maintainer__ = "maldevel"

import argparse
import os
import re
import sys
import time
from argparse import RawTextHelpFormatter
from sys import platform as _platform
from urllib.parse import urlparse
from typing import Optional, List, Dict

import requests
import validators
from termcolor import colored

if _platform == 'win32':
    import colorama

    colorama.init()


class MyParser:

    def __init__(self):
        self.temp: List[str] = []

    def extract(self, results: str, word: str) -> None:
        self.results = results
        self.word = word

    def generic_clean(self) -> None:
        for e in '''<KW> </KW> </a> <b> </b> </div> <em> </em> <p> </span>
                    <strong> </strong> <title> <wbr> </wbr>'''.split():
            self.results = self.results.replace(e, '')
        for e in '%2f %3a %3A %3C %3D & / : ; < = > \\'.split():
            self.results = self.results.replace(e, ' ')

    def emails(self) -> List[str]:
        self.generic_clean()
        reg_emails = re.compile(
            r'[a-zA-Z0-9.\-_+#~!$&\',;=:]+' +
            r'@' +
            r'[a-zA-Z0-9.-]*' +
            self.word)
        self.temp = reg_emails.findall(self.results)
        return self.unique()

    def unique(self) -> List[str]:
        return list(set(self.temp))


class EmailHarvester:

    def __init__(self, user_agent: str, proxy: Optional[urlparse] = None) -> None:
        self.plugins: Dict[str, Dict[str, callable]] = {}
        self.proxy = proxy
        self.user_agent = user_agent
        self.parser = MyParser()
        self.active_engine = "None"
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")

        sys.path.insert(0, path)
        for f in os.listdir(path):
            fname, ext = os.path.splitext(f)
            if ext == '.py':
                mod = __import__(fname, fromlist=[''])
                self.plugins[fname] = mod.Plugin(self, {'useragent': user_agent, 'proxy': proxy})

    def register_plugin(self, search_method: str, functions: Dict[str, callable]) -> None:
        self.plugins[search_method] = functions

    def get_plugins(self) -> Dict[str, Dict[str, callable]]:
        return self.plugins

    def show_message(self, msg: str) -> None:
        print(green(msg))

    def init_search(self, url: str, word: str, limit: int, counter_init: int, counter_step: int,
                    engine_name: str) -> None:
        self.results = ""
        self.totalresults = ""
        self.limit = limit
        self.counter = counter_init
        self.url = url
        self.step = counter_step
        self.word = word
        self.active_engine = engine_name

    def do_search(self) -> None:
        try:
            urly = self.url.format(counter=str(self.counter), word=self.word)
            headers = {'User-Agent': self.user_agent}
            if self.proxy:
                proxies = {self.proxy.scheme: "http://" + self.proxy.netloc}
                r = requests.get(urly, headers=headers, proxies=proxies)
            else:
                r = requests.get(urly, headers=headers)
        except Exception as e:
            print(e)
            sys.exit(4)

        if r.encoding is None:
            r.encoding = 'UTF-8'

        self.results = r.content.decode(r.encoding)
        self.totalresults += self.results

    def process(self) -> None:
        while self.counter < self.limit:
            self.do_search()
            time.sleep(1)
            self.counter += self.step
            print(
                green("[+] Searching in {}:".format(self.active_engine)) + cyan(
                    " {} results".format(str(self.counter))))

    def get_emails(self) -> List[str]:
        self.parser.extract(self.totalresults, self.word)
        return self.parser.emails()


def yellow(text: str) -> str:
    return colored(text, 'yellow', attrs=['bold'])


def green(text: str) -> str:
    return colored(text, 'green', attrs=['bold'])


def red(text: str) -> str:
    return colored(text, 'red', attrs=['bold'])


def cyan(text: str) -> str:
    return colored(text, 'cyan', attrs=['bold'])


def unique(data: List[str]) -> List[str]:
    return list(set(data))


def check_proxy_url(url: str) -> urlparse:
    url_checked = urlparse(url)
    if url_checked.scheme not in ('http', 'https') or url_checked.netloc == '':
        raise argparse.ArgumentTypeError('Invalid {} Proxy URL (example: http://127.0.0.1:8080).'.format(url))
    return url_checked


def limit_type(x: str) -> int:
    x = int(x)
    if x > 0:
        return x
    raise argparse.ArgumentTypeError("Minimum results limit is 1.")


def check_domain(value: str) -> str:
    domain_checked = validators.domain(value)
    if not domain_checked:
        raise argparse.ArgumentTypeError('Invalid {} domain.'.format(value))
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="""
    A tool to retrieve Domain email addresses from Search Engines | @maldevel
                                {}: {}
""".format(red('Version'), yellow(__version__)), formatter_class=RawTextHelpFormatter)

    parser.add_argument("-d", '--domain', action="store", metavar='DOMAIN', dest='domain',
                        default=None, type=check_domain, help="Domain to search.")
    parser.add_argument("-s", '--save', action="store", metavar='FILE', dest='filename',
                        default=None, type=str, help="Save the results into a TXT and XML file (both).")

    parser.add_argument("-e", '--engine', action="store", metavar='ENGINE', dest='engine',
                        default="all", type=str, help="Select search engine plugin(eg. '-e google').")

    parser.add_argument("-l", '--limit', action="store", metavar='LIMIT', dest='limit',
                        type=limit_type, default=100, help="Limit the number of results.")
    parser.add_argument('-u', '--user-agent', action="store", metavar='USER-AGENT', dest='uagent',
                        type=str, help="Set the User-Agent request header.")
    parser.add_argument('-x', '--proxy', action="store", metavar='PROXY', dest='proxy',
                        default=None, type=check_proxy_url, help="Setup proxy server (eg. '-x http://127.0.0.1:8080')")
    parser.add_argument('--noprint', action='store_true', default=False,
                        help='EmailHarvester will print discovered emails to terminal. It is possible to tell EmailHarvester not to print results to terminal with this option.')
    parser.add_argument('-r', '--exclude', action="store", metavar='EXCLUDED_PLUGINS', dest="exclude",
                        type=str, default=None,
                        help="Plugins to exclude when you choose 'all' for search engine (eg. '-r google,twitter')")
    parser.add_argument('-p', '--list-plugins', action='store_true', dest='listplugins',
                        default=False, help='List all available plugins.')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    args = parser.parse_args()

    if args.listplugins:
        path = "plugins/"
        print(green("[+] Available plugins"))
        sys.path.insert(0, path)
        for f in os.listdir(path):
            fname, ext = os.path.splitext(f)
            if ext == '.py':
                print(green("[+] Plugin: ") + cyan(fname))
        sys.exit(1)

    if not args.domain:
        print(red("[-] Please specify a domain name to search."))
        sys.exit(2)
    domain = args.domain

    user_agent = args.uagent or "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1"

    print(green("[+] User-Agent in use: ") + cyan(user_agent))

    if args.proxy:
        print(green("[+] Proxy server in use: ") + cyan(args.proxy.scheme + "://" + args.proxy.netloc))

    filename = args.filename or ""
    limit = args.limit
    engine = args.engine
    app = EmailHarvester(user_agent, args.proxy)
    plugins = app.get_plugins()

    all_emails: List[str] = []
    excluded: List[str] = []
    if args.exclude:
        excluded = args.exclude.split(',')
    if engine == "all":
        print(green("[+] Searching everywhere"))
        for search_engine in plugins:
            if search_engine not in excluded:
                all_emails += plugins[search_engine]['search'](domain, limit)
    elif engine not in plugins:
        print(red("[-] Search engine plugin not found"))
        sys.exit(3)
    else:
        all_emails = plugins[engine]['search'](domain, limit)
    all_emails = unique(all_emails)

    if not all_emails:
        print(red("[-] No emails found"))
        sys.exit(4)

    print(green("[+] Emails found: ") + cyan(str(len(all_emails))))

    if not args.noprint:
        for email in all_emails:
            print(email)

    if filename:
        try:
            print(green("[+] Saving results to files"))
            with open(filename, 'w') as out_file:
                for email in all_emails:
                    try:
                        out_file.write(email + "\n")
                    except Exception as e:
                        print(red("[-] Exception: " + str(e)))
        except Exception as e:
            print(red("[-] Error saving TXT file: " + str(e)))

        try:
            filename = filename.split(".")[0] + ".xml"
            with open(filename, 'w') as out_file:
                out_file.write('<?xml version="1.0" encoding="UTF-8"?><EmailHarvester>')
                for email in all_emails:
                    out_file.write('<email>{}</email>'.format(email))
                out_file.write('</EmailHarvester>')
            print(green("[+] Files saved"))
        except Exception as e:
            print(red("[-] Error saving XML file: " + str(e)))


if __name__ == '__main__':
    main()

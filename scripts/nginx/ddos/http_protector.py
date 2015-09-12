import sys
import argparse
import traceback
import os

from lib.data_providers import StdInDataProvider, FileDataProvider
from lib.nginx_log_parser import NginxLogParser
from lib.analyzers import GenericDDoSAnalyzer
from lib.blockers import ApfBlocker, IPTablesBlocker


def enter_pid_lock(lock_file):
    assert lock_file

    if os.path.exists(lock_file):
        sys.exit()

    pid = str(os.getpid())
    file(lock_file, 'w').write(pid)


def exit_pid_lock(lock_file):
    assert lock_file

    if os.path.exists(lock_file):
        os.remove(lock_file)


def main():
    known_formats = {
        'nginx': NginxLogParser
    }
    known_blockers = {
        'apf': ApfBlocker,
        'iptables': IPTablesBlocker
    }

    parser = argparse.ArgumentParser(description='HTTP flood analyzer',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-p", dest="pidfile", required=True, metavar="pid-file", help="PID lock file")
    parser.add_argument("-f", "--format", dest="log_format", choices=known_formats.keys(),
                        required=True, default='nginx', help="Log file format.")
    parser.add_argument("-b", "--blocker", choices=known_blockers.keys(),
                        required=True, default='iptables', help="Use specific blocker.")

    group1 = parser.add_argument_group('Parser parameters.')
    mutex_group1 = group1.add_mutually_exclusive_group()
    mutex_group1.add_argument("--stdin", dest="stdin", action='store_true', help="Data from stdin")
    mutex_group1.add_argument("-l", "--log", dest="log_file", help="Log file to process.")

    args = parser.parse_args()

    enter_pid_lock(args.pidfile)
    try:
        # input
        if args.stdin:
            data_provider = StdInDataProvider()
        else:
            data_provider = FileDataProvider(args.log_file)

        # log parser
        log_parser = known_formats[args.log_format](data_provider)

        # select blocker
        blocker = known_blockers[args.blocker]()

        # select analyzer
        analyzer = GenericDDoSAnalyzer(log_parser, threshold=10)

        for attacker_ip in analyzer.attacker_ip_list():
            blocker.block(attacker_ip)
            sys.stdout.write("IP %s blocked.\n" % attacker_ip)

    finally:
        exit_pid_lock(args.pidfile)


if __name__ == "__main__":
    try:
        main()
    except Exception, ex:
        traceback.print_exc(file=sys.stdout)
        exit(1)

    exit(0)
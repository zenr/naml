import argparse

from session import Session, Data, parse_opts

if __name__=='__main__':
    args = parse_opts()
    data = Data()
    sess = Session(args, '.')

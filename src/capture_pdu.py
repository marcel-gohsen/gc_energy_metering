import argparse
import time

from listeners.pdu_listener import PDUListener


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Listen for energy values of PDU outlets")
    parser.add_argument("-outlets", metavar="[0,17]", required=True, nargs="+")
    parser.add_argument("-duration", metavar="seconds", required=True, type=int)
    parser.add_argument("-exp", type=str, required=True)
    args = parser.parse_args()

    listener = PDUListener(sample_rate=4, outlets=args.outlets, experiment=args.exp)
    listener.start()
    time.sleep(int(args.duration))
    listener.stop()

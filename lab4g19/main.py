import sys
import logging
import optparse
import json
import os
import os.path
import scapy.layers.inet
from scapy.utils import PcapReader
from scapy.error import Scapy_Exception

from conversation import Connection_keeper
from recog import recognizer, filename_and_payload
from constants import DUMP_DIR

file_trace_id = 1
extracted_files = 0
generated_traces = 0


def callback(payload):
    """
    Write extracted payload to file
    """
    global extracted_files
    filename, payload = filename_and_payload(payload)
    if not os.path.isdir(DUMP_DIR):
        os.makedirs(DUMP_DIR)
    filename = os.path.join(DUMP_DIR, filename)
    logging.info("Writing extracted file: {0}".format(filename))
    open(filename, "w").write(payload)
    extracted_files += 1


def tracer(trace):
    """
    Write generated trace to file
    """
    global generated_traces
    global file_trace_id
    if not os.path.isdir(DUMP_DIR):
        os.makedirs(DUMP_DIR)
    filename = os.path.join(DUMP_DIR, "trace_" + str(file_trace_id) + '.json')
    file_trace_id += 1
    with open(filename, 'w') as file:
        logging.info("Writing generated trace: {0}".format(filename))
        json.dump(trace, file, indent=4, separators=(',', ': '))
    generated_traces += 1


def main():
    """
    Proccessing arguments, configure logger and
    call to Connection_keeper for start  file extraction and
    trace generation.
    """
    global tracer
    global extracted_files
    global generated_traces
    # Arguments parsing
    parser = optparse.OptionParser(usage="usage: %prog [options] filename")
    parser.add_option("-t", "--trace", action="store_true", dest="trace",
                      help="Generate traces of the STDs.", default=False)
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="Make lots of noise.", default=False)
    options, args = parser.parse_args()
    if len(args) != 1:
        sys.stderr.write("Please enter an input capture filename\n")
        parser.print_help()
        sys.exit(1)

    trace = bool(options.trace)
    if trace:
        tracer = tracer
    else:
        tracer = None

    verbose = bool(options.verbose)
    if verbose:
        logging.basicConfig(stream=sys.stdout,
                            format='%(levelname)s:%(message)s',
                            level=logging.DEBUG)
    else:
        logging.basicConfig(stream=sys.stdout,
                            format='%(levelname)s:%(message)s',
                            level=logging.INFO)

    filename = args[0]
    logging.info("Input capture filename: {0}".format(filename))

    ck = Connection_keeper(recognizer, callback, tracer=tracer)
    try:
        for x in PcapReader(filename):
            ck.add(x)
        ck.save()
    except KeyboardInterrupt:
        logging.error("Program cancelled by user")
    except IOError as e:
        logging.error("I/O Error: {0}".format(e))
    else:
        logging.info("Extracted files: {0}".format(extracted_files))
        if trace:
            logging.info("Generated traces: {0}".format(generated_traces))
    logging.info("Exiting the program")

if __name__ == "__main__":
    main()

import sys, os


class ErrorHandler:
    @staticmethod
    def handle(prefix, msg, exception, file=sys.stderr, terminate=True):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]

        print("[" + prefix + "]: " + msg + " (" + fname + "," + str(exc_tb.tb_lineno) + ")", file=file)

        if exception is not None:
            if len(str(exception)) > 0:
                print("[" + prefix + "]: " + str(exception), file=file)

        if terminate:
            exit(1)

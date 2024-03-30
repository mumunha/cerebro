import requests


def download_file_func(message, token):
    
    if message.audio is not None:
        file_id = message.audio.file_id
    elif message.voice is not None:
        file_id = message.voice.file_id

    # Get the file path from the Telegram API
    file_info_url = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
    file_info_response = requests.get(file_info_url)
    file_info = file_info_response.json()
    file_path = file_info['result']['file_path']

    # Download the file
    download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    response = requests.get(download_url)

    # Save the file locally
    local_file_path = "download.ogg"  # Specify your desired file path
    with open(local_file_path, 'wb') as file:
        file.write(response.content)

    
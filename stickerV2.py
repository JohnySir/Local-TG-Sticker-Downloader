import os
import json
import requests
from PIL import Image
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

# -----------------------------------------------------------------------------
# CONFIGURABLE SETTINGS
# -----------------------------------------------------------------------------
# This script requires the 'requests' and 'Pillow' libraries.
# You can install them using pip:
# pip install requests Pillow

# --- Telegram Bot Token ---
# Your Telegram bot token.
BOT_TOKEN = "YOUR_BOT_TOKEN"

# --- Sticker Pack Link ---
# The link to the Telegram sticker pack you want to download.
STICKER_PACK_LINK = "https://t.me/addstickers/UtyaTheDuck"

# --- Output Folder ---
# The folder where the downloaded stickers will be saved.
OUTPUT_FOLDER = "stickers"
# The name of the file to store the bot token.
CONFIG_FILE = "config.json"


# -----------------------------------------------------------------------------
# SCRIPT LOGIC (No need to edit below this line)
# -----------------------------------------------------------------------------

class TelegramStickerDownloader:
    """
    A class to download and convert Telegram sticker packs to PNG images.
    """

    def __init__(self, bot_token):
        """
        Initializes the downloader with a Telegram bot token.
        """
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/"
        self.console = Console()

    def _make_api_request(self, endpoint, params=None):
        """
        Makes a request to the Telegram Bot API.
        """
        url = self.api_url + endpoint
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.console.print(f"[bold red]Error making API request:[/bold red] {e}")
            return None

    def _get_sticker_set(self, pack_name):
        """
        Retrieves information about a sticker pack.
        """
        params = {'name': pack_name}
        return self._make_api_request('getStickerSet', params)

    def _get_file_info(self, file_id):
        """
        Retrieves file information for a given file ID.
        """
        params = {'file_id': file_id}
        return self._make_api_request('getFile', params)

    def _download_file(self, file_path, save_path, progress, task_id):
        """
        Downloads a file and updates the progress bar.
        """
        url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            progress.update(task_id, total=total_size)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    progress.update(task_id, advance=len(chunk))
        except requests.exceptions.RequestException as e:
            self.console.print(f"[bold red]Error downloading file:[/bold red] {e}")

    def _convert_webp_to_png(self, webp_path, png_path):
        """
        Converts a WEBP image to PNG format.
        """
        try:
            with Image.open(webp_path) as img:
                img.save(png_path, 'PNG')
            os.remove(webp_path)
        except Exception as e:
            self.console.print(f"[bold red]Error converting image:[/bold red] {e}")

    def download_sticker_pack(self, sticker_pack_link, output_folder):
        """
        Downloads all stickers from a sticker pack link.
        """
        pack_name = sticker_pack_link.split('/')[-1]
        
        with self.console.status("[bold green]Fetching sticker pack info...[/bold green]"):
            pack_info = self._get_sticker_set(pack_name)

        if not pack_info or not pack_info.get("ok"):
            self.console.print("[bold red]Could not retrieve sticker pack information. Please check the link and your bot token.[/bold red]")
            return

        pack_folder = os.path.join(output_folder, pack_name)
        os.makedirs(pack_folder, exist_ok=True)

        self.console.print(Panel(f"[bold cyan]Downloading Sticker Pack:[/bold cyan] [yellow]{pack_info['result']['title']}[/yellow]", border_style="green"))
        
        stickers = pack_info['result']['stickers']
        with Progress(
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            TimeElapsedColumn(),
            "•",
            TimeRemainingColumn(),
            console=self.console
        ) as progress:
            download_task = progress.add_task("[green]Downloading[/green]", total=len(stickers))
            convert_task = progress.add_task("[magenta]Converting[/magenta]", total=len(stickers))

            for sticker in stickers:
                file_info = self._get_file_info(sticker['file_id'])
                if file_info and file_info.get("ok"):
                    file_path = file_info['result']['file_path']
                    file_extension = os.path.splitext(file_path)[1]
                    
                    # --- FIX: Use file_unique_id for unique filenames ---
                    file_unique_id = sticker['file_unique_id']
                    # Sanitize emoji for filename, keeping it simple
                    sanitized_emoji = ''.join(c for c in sticker.get('emoji', 'sticker') if c.isalnum())
                    
                    # Generate a unique filename using the unique ID
                    file_name = f"{file_unique_id}_{sanitized_emoji}{file_extension}"
                    webp_save_path = os.path.join(pack_folder, file_name)

                    self._download_file(file_path, webp_save_path, progress, download_task)
                    
                    # Convert to PNG using the same unique naming scheme
                    if file_extension.lower() == ".webp":
                        png_file_name = f"{file_unique_id}_{sanitized_emoji}.png"
                        png_save_path = os.path.join(pack_folder, png_file_name)
                        self._convert_webp_to_png(webp_save_path, png_save_path)
                    
                    progress.update(convert_task, advance=1)
                progress.update(download_task, advance=1)


        self.console.print(Panel("[bold green]Sticker pack download complete![/bold green]", border_style="green"))

def load_token():
    """Loads the bot token from the config file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get("bot_token")
        except json.JSONDecodeError:
            return None
    return None

def save_token(token):
    """Saves the bot token to the config file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"bot_token": token}, f)

def main():
    """Main function to run the sticker downloader."""
    console = Console()
    console.print(Panel(
        "[bold magenta]TG Sticker Downloader[/bold magenta]",
        title="[bold blue]Welcome![/bold blue]",
        subtitle="[bold red]By Johny[/bold red]",
        border_style="bold purple",
        expand=False
    ))

    bot_token = load_token()
    if not bot_token:
        console.print("[yellow]No saved bot token found.[/yellow]")
        bot_token = Prompt.ask("[bold yellow]Please enter your Telegram Bot Token[/bold yellow]")
        save_token(bot_token)
        console.print("[bold green]Bot token saved for future sessions.[/bold green]")
    else:
        console.print("[bold green]Saved bot token loaded.[/bold green]")

    downloader = TelegramStickerDownloader(bot_token)
    
    while True:
        sticker_pack_link = Prompt.ask("\n[bold yellow]Enter the sticker pack link (or type 'quit' to exit)[/bold yellow]")
        if sticker_pack_link.lower() == 'quit':
            break
        
        downloader.download_sticker_pack(sticker_pack_link, OUTPUT_FOLDER)

if __name__ == '__main__':
    main()
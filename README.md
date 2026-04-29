<div align="center">
    <h1>115Bot - Telegram Bot</h1>
    <p>English | <a href="./README.md">[简体中文]</a></p>
</div>

A Python-based Telegram bot for managing and controlling 115 Network Disk, supporting offline downloads, video uploads, directory synchronization, and more.

## Tg group

Usage Issues & Bug Reports

[Join](https://t.me/+FTPNla_7SCc3ZWVl)

## Update Log
v3.2.1
- Added crawling filter rule configuration, allowing precise scraping through title keyword regex. Matched resources can also be assigned to specific save directories for easy categorization. For rule configuration details, please refer to the instructions in "/config/crawling_strategy.yaml".
- Optimized request strategies, significantly reducing API request frequency.
- Code improvements and bug fixes.

v3.2.0
- Added SeHua spider, crawl sehua data you specify and offline download them to 115 every midnight.
- Updated interaction experience. Command "/dl", "/av" update to async model, offline download to 115 will not block. Both of the max download queue is 5.
- Updated interaction flow. If you want to add a record to retry list, you must to specify the TMDB name. Once the retry succeeds, the bot will never ask for it again.
- Added “/reload” command to reload configuration
- Added a log file. By default, it will be saved in "/config/115bot.log" and overwritten when the container restarts.
- Code optimization and bug fixes

v3.1.0
- Removed AV subscription feature, added AV daily update functionality that automatically updates and downloads the latest resources to 115 daily, can be enabled or disabled in the configuration file. If the offline download fails, the bot will retry every 6 hours until successful.
- Added direct AV number offline download feature, input 'av ipz-266' to automatically download to 115, eliminating the need to search for magnet links
- A new “Retry List” feature has been added. When offline access fails, you can add it to the retry list, and the robot will attempt offline access again after a fixed interval. When you no longer need it, you can clear this list at any time.
- Added bot menu
- Code optimization and bug fixes

v3.0.0
- Refactored underlying interface, all 115 requests now use the open platform API for faster and more stable performance!
- Optimized video file upload, supporting large video uploads
- Temporarily disabled AV subscription feature, will update when a stable and reliable interface is found

v2.3.7
- Fixed the bug where subscription wasn't automatically cancelled after manually downloading subscribed movies

v2.3.6
- Fixed error with subscribe movie download
- Due to the triggering of JAVDB's anti-crawling mechanism, the crawling failed and the AV subscription function was temporarily closed. A stable solution will be updated later.

v2.3.5
- Fixed escaping errors in MarkdownV2 formatting for offline download timeout alert messages  
- Optimized movie subscription download logic  

v2.3.4
- bug fix

v2.3.3
- bug fix

v2.3.2
- bug fix

v2.3.1
- When the actress subscription offline download failed, bot will try to change the magnet link

v2.3.0
- Added movie subscription feature
- Fixed various bugs

v2.2.0
- Fixed various bugs

## Background
This project originated from the need to optimize personal daily viewing experience. As a movie enthusiast, I use the combination of 115 Network Disk + CloudDrive2 + Emby to manage and watch media content.

Imagine this scenario:

While commuting, you come across an interesting movie. Simply send the magnet link to the TG bot, and it will:
- Automatically download the movie to the specified category directory in 115 Network Disk
- Intelligently clean up advertisement files

When you return home after work, just open 115 and enjoy a well-organized collection.

## Known Issues
- Limited support for TV series. Downloading series directly may cause unexpected issues
- Directory synchronization will clear the entire folder, including metadata (quite aggressive)

If you'd like to help improve this project, welcome to [join](https://t.me/qiqiandfei)!

## Features

- � **115 Account Management**
  - Based on 115 Open Platform
  - Uses official API for stable and reliable service

- ⬇️ **Offline Download**
  - Support multiple download protocols: Magnet links, Thunder, ed2k, FTP, HTTPS
  - Intelligent automatic category storage
  - Advertisement file cleanup

- 🎬 **AV Number Download**
  - Input AV number to automatically download offline
  - Intelligent advertisement file cleanup

- 🎭 **Movie Subscription**
  - Support automatic movie resource subscription
  - Automatic offline download when new resources are available
  - Intelligent advertisement file cleanup

- 🔄 **Directory Synchronization**
  - Automatic local directory sync

- � **Video Processing**
  - Support automatic video file upload to 115 Network Disk (Note: Consumes VPS/proxy traffic, use with caution)

## Quick Start

### Requirements

- Docker environment
- Python 3.12+
- Accessible Telegram network environment
- Chrome/Chromium for Selenium-based crawling features when running locally

### Local Development

The Docker image reads `/config/config.yaml`. For local development, use `scripts/dev.sh`; it sets `TG115_DEBUG=1` so the app reads project-local paths such as `config/config.yaml`, `tmp`, and `app/images`.

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
mkdir -p config tmp media CloudNAS
cp config/config.yaml.example config/config.yaml
./scripts/dev.sh
```

Before starting, fill at least these values in `config/config.yaml`:
- `bot_token`
- `allowed_user`
- `115_app_id`, or both `access_token` and `refresh_token`

### Installation

1. **Clone Project**
   ```bash
   git clone https://github.com/qiqiandfei/Telegram-115bot.git
   cd 115bot
   ```

2. **Configure Settings**
   - Copy configuration template
     ```bash
     cp config/config.yaml.example config/config.yaml
     ```
   - Edit `config.yaml`, fill in necessary configurations:
     - Telegram Bot Token
     - Telegram authorized user
     - 115 Network Disk configuration
     - Directory mapping settings

3. **Docker Deployment**

   **Local**
   ```bash
   # Build base image
   docker build -t 115bot:base -f Dockerfile.base .
   
   # Build application image
   docker build -t 115bot:latest .
   
   # Run container
   docker run -d \
     --name tg-bot-115 \
     --restart unless-stopped \
     -e TZ=Asia/Shanghai \
     -v /path/to/config:/config \
     -v /path/to/tmp:/tmp \
     115bot:latest
   ```
   
   **Docker Compose (Recommended)**
   ```yaml
   version: '3.8'
   services:
    115-bot:
      container_name: tg-bot-115
      environment:
        TZ: Asia/Shanghai
      image: qiqiandfei/115-bot:latest
      # privileged: True
      restart: unless-stopped
      volumes:
        - /path/to/config:/config  # Configuration path
        - /path/to/tmp:/tmp        # Temp path
   ```

## Configuration

Please refer to the comments in `config/config.yaml.example` for configuration details.

### Directory Structure
```
.
├── app
│   ├── 115bot.py                 # Entry point script
│   ├── config.yaml.example       # Template of configuration
│   ├── core                      # Core functions
│   ├── handlers                  # Telegram handlers
│   ├── images                    # Images
│   ├── init.py                   # Init script
│   └── utils                     # Utils
├── build.sh                      # local build shell
├── config                        # dir of configuration
├── create_tg_session_file.py     # create tg_session file
├── docker-compose.yaml           # docker-compose
├── Dockerfile                    
├── Dockerfile.base
├── legacy                        
├── LICENSE
├── README_EN.md
├── README.md
├── requirements.txt              
```

## Usage Guide

### Basic Commands

- `/start`      - Show help information
- `/reload`     - Reload the configuration
- `/rl`         - Retry list
- `/csh [date]` - Manually trigger sehua crawl
- `/sync`       - Sync directory

### 115 Open Platform Application

**Strongly recommend applying for 115 Open Platform for better user experience**
- Application URL: [115 Open Platform](https://open.115.com/)
- After approval, fill in the `115_app_id` in the configuration file

If you don't want to use the 115 Open Platform, please use the previous image version `qiqiandfei/115-bot:v2.3.7`

### Video Download Configuration

Due to Telegram Bot API limitations, videos larger than 20MB cannot be downloaded. To download large videos, please configure the Telegram client:

#### Configuration
Telegram API application address: [Telegram Development Platform](https://my.telegram.org/auth)

When your application is successful, you will receive a “tg_api_id” and “tg_api_hash”.

Ensure that these three parameters are correct:
```
# bot_name
bot_name: "@yourbotname"

# telegram api info
tg_api_id: 1122334
tg_api_hash: 1yh3j4k9dsk0fj3jdufnwrhf62j1k33f
```

> **Note**: If you don't configure this step, the bot will still work normally, but cannot handle video files larger than 20MB.

### Important Warning

⚠️ **Synchronization Function Warning**: The `/sync` command will **delete all files in the target directory**, including metadata. Large-scale synchronization operations may trigger 115 Network Disk's risk control mechanism, please use with caution!

### License
```
MIT License

Copyright (c) 2025 qiqiandfei

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
## Disclaimer
This project is intended solely for educational and research purposes. Please comply with all applicable laws and regulations, and refrain from using it for commercial purposes. Users assume all risks associated with its use!

If this project has been helpful to you, please give it a ⭐!

## Buy me a coffee~
![Buy me a coffee](https://alist.qiqiandfei.fun:8843/d/Syncthing/yufei/%E4%B8%AA%E4%BA%BA/%E8%B5%9E%E8%B5%8F.png)

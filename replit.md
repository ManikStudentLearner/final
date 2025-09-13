# SkyBlock Auction Bot

## Overview

This is a Discord bot designed to monitor Hypixel SkyBlock auctions for specific sheep skin items. The bot continuously tracks auctions through the Hypixel API and notifies users in a designated Discord channel when targeted sheep skins become available. It features memory management to prevent duplicate notifications and includes automatic cleanup mechanisms.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
- **Discord.py**: Uses the discord.py library with the commands extension for Discord integration
- **Async Architecture**: Built on asyncio for non-blocking API calls and concurrent operations
- **Minimal Intents**: Configured with default intents but disabled message content reading for efficiency

### Data Management
- **In-Memory Storage**: Uses dictionaries and sets for tracking seen auctions and target items
- **Time-Based Cleanup**: Implements automatic memory cleanup every hour to prevent memory leaks
- **Auction Deduplication**: Maintains a 24-hour memory of processed auctions using UUID tracking

### API Integration
- **Hypixel SkyBlock API**: Polls the auctions endpoint for real-time auction data
- **Rate Limiting Consideration**: Designed to handle API rate limits gracefully
- **Optional Authentication**: Supports Hypixel API key for enhanced rate limits

### Configuration Management
- **Environment Variables**: All sensitive data and configuration stored as environment variables
- **Target Item Management**: Hardcoded set of sheep skins with easy modification capability
- **Channel-Specific Notifications**: Configurable Discord channel for auction alerts

## External Dependencies

### APIs
- **Hypixel SkyBlock API**: Primary data source for auction information at `https://api.hypixel.net/skyblock/auctions`
- **Discord API**: Bot interaction through discord.py library

### Python Libraries
- **discord.py**: Discord bot framework and API wrapper
- **aiohttp**: Asynchronous HTTP client for API requests
- **asyncio**: Core async/await functionality

### Environment Requirements
- **DISCORD_TOKEN**: Discord bot authentication token (required)
- **CHANNEL_ID**: Target Discord channel ID for notifications (required)  
- **HYPIXEL_API_KEY**: Optional Hypixel API key for enhanced rate limits

### Target Items
- Predefined set of sheep skin variants: Dark Green, Orange, Red, Blue, Gray, Yellow, and Monster Sheep Skins
import requests
import json
import asyncio
from rustplus import RustSocket, ServerDetails, ChatCommand, CommandOptions
from rustplus.commands.chat_command import ChatCommandTime
from rustplus import EntityEventPayload, TeamEventPayload, ChatEventPayload, ProtobufEvent, ChatEvent, EntityEvent, TeamEvent

def register():
    auth = "eyJzdGVhbUlkIjoiNzY1NjExOTgwNjQxNDYzMzUiLCJ2ZXJzaW9uIjowLCJpc3MiOjE3MjU4NDkwMTgsImV4cCI6MTcyNzA1ODYxOH0=.Atp6/JjUbuiz9rUCCF8feo0amncWw5mJh67+46yTpxuSgQLVMxpaDXB5NzyxnGpMY8x+WjzYF1eF5a+k5WJUCQ=="

    url = 'https://companion-rust.facepunch.com/api/history/read'
    data = {
    'AuthToken': auth
}

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        history_data = response.json()

        for item in history_data:
            steamId = item['steamId']
        
        # Parse the 'data' field as JSON
            item_data = json.loads(item['data'])
        
        # Check if all required fields exist in the parsed data
            if all(key in item_data for key in ['playerToken', 'ip', 'port']):
                playerToken = item_data['playerToken']
                ip = item_data['ip']
                port = item_data['port']
                print(f"SteamID: {steamId}")
                print(f"PlayerToken: {playerToken}")
                print(f"IP: {ip}")
                print(f"Port: {port}")
                break  # Exit after finding the first valid set of information
        else:
            print("No valid information set found.")

    except requests.exceptions.RequestException as error:
        print(error)
    return steamId,playerToken,ip,port

steamId, playerToken, ip, port = register()


server_details = ServerDetails(ip, port, steamId, playerToken)
socket = RustSocket(server_details, debug=False)

# New command system
commands = {}

def register_command(name, aliases=None):
    def decorator(func):
        commands[name] = func
        if aliases:
            for alias in aliases:
                commands[alias] = func
        return func
    return decorator

# Convert existing commands to use the new system
@register_command('promote', aliases=['lead', 'leader'])
async def promote(command: ChatCommand):
    sender_steam_id = command.sender_steam_id
    try:
        response = await socket.promote_to_team_leader(sender_steam_id)
        if response:
            await socket.send_team_message(f"Promoted {sender_steam_id} to team leader")
        else:
            await socket.send_team_message(f"Failed to promote {sender_steam_id}")
    except Exception as e:
        await socket.send_team_message(f"Failed to promote {sender_steam_id}: {str(e)}")


@register_command('info', aliases=['pop', 'serverinfo'])
async def info(command: ChatCommand):
    rustinfo = await socket.get_info()
    message_part1 = (
        f"Server Info:  "
        f"URL: {rustinfo.url}   "
        f"Name: {rustinfo.name}   "
        f"Size: {rustinfo.size}   "
    )
    message_part2 = (
        f"Players: {rustinfo.players}   "
        f"Max Players: {rustinfo.max_players}   "
        f"Queued Players: {rustinfo.queued_players}   "
        f"Seed: {rustinfo.seed}"
    )
    await socket.send_team_message(message_part1)
    await socket.send_team_message(message_part2)

BASE_URL = 'https://0f0lrr2w6d.execute-api.us-west-1.amazonaws.com/api'

async def api_request(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as error:
        print(f"API request error: {error}")
        return None

@register_command('item')
async def get_item(command: ChatCommand):
    print(command.args)
    args = command.args
    if not args:
        await socket.send_team_message("Please provide an item name or ID.")
        return
    
    item_query = ' '.join(args)
    params = {
    'filters': json.dumps({
        'name': {'column': 'name', 'comparator': 'CONTAINS', 'value': item_query}
    }),
    'orderBy': json.dumps([{'order1': {'column': 'name', 'descending': False}}]),
    'limit': '5'
    }
    data = await api_request('items')
    
    if data:
        item = data[0]
        message_part1 = f"Item: {item['name']} (ID: {item['id']})   "
        message_part1 += f"Stack size: {item['stack_size']}, Despawn time: {item['despawn_time']}s   "
        
        message_part2 = f"Projectile weapon: {item['is_projectile_weapon']}, Melee weapon: {item['is_melee_weapon']}   "
        message_part2 += f"Deployable: {item['is_deployable']}, Consumable: {item['is_consumable']}"
        
        await socket.send_team_message(message_part1)
        await socket.send_team_message(message_part2)
    else:
        await socket.send_team_message(f"No item found matching '{item_query}'.")

@register_command('craft')
async def get_craft(command: ChatCommand):
    if not command.args:
        await socket.send_team_message("Please provide an item name to get crafting info.")
        return
    
    item_query = ' '.join(command.args)
    params = {'filters': json.dumps({'name': {'column': 'name', 'comparator': 'CONTAINS', 'value': item_query}})}
    data = await api_request('craft')
    
    if data and data['recipes']:
        recipe = data['recipes'][0]
        message = f"Crafting recipe for {recipe['result_item']} (x{recipe['result_amount']}):   "
        for ingredient, amount in recipe['ingredients'].items():
            message += f"- {ingredient}: {amount}   "
        await socket.send_team_message(message)
    else:
        await socket.send_team_message(f"No crafting recipe found for '{item_query}'.")

@register_command('durability')
async def get_durability(command: ChatCommand):
    if not command.args:
        await socket.send_team_message("Please provide an item name to get durability info.")
        return
    
    item_query = ' '.join(command.args)
    params = {'tool': {'CONTAINS': item_query}}
    data = await api_request('durability')
    
    if data and data['durability']:
        dur = data['durability'][0]
        message = f"Durability info for {dur['tool']}:   "
        message += f"Type: {dur['durability_type']}, Category: {dur['category']}   "
        message += f"Quantity: {dur['quantity']}, Time: {dur['time']}s   "
        message += f"Fuel: {dur['fuel']}, Sulfur: {dur['sulfur']}"
        await socket.send_team_message(message)
    else:
        await socket.send_team_message(f"No durability info found for '{item_query}'.")

@register_command('loot')
async def get_loot(command: ChatCommand):
    if not command.args:
        await socket.send_team_message("Please provide a container name to get loot info.")
        return
    
    container_query = ' '.join(command.args)
    params = {'container': {'EQUALS': container_query}}
    data = await api_request('loot', params)
    
    if data and data['loot']:
        message = f"Loot table for {container_query}:   "
        for item in data['loot'][:5]:  # Limit to 5 items to avoid long messages
            message += f"- {item['item']}: {item['chance']}% chance, Amount: {item['amount']}   "
        await socket.send_team_message(message)
    else:
        await socket.send_team_message(f"No loot info found for '{container_query}'.")

@register_command('recycle')
async def get_recycle(command: ChatCommand):
    if not command.args:
        await socket.send_team_message("Please provide an item name to get recycling info.")
        return
    
    item_query = ' '.join(command.args)
    params = {'recycler_name': {'CONTAINS': item_query}}
    data = await api_request('recycle', params)
    
    if data and data['recycle']:
        recycle = data['recycle'][0]
        message = f"Recycling info for {recycle['recycler_name']}:   "
        message += f"Efficiency: {recycle['efficiency']}%   "
        message += "Yield:   "
        for item, amount in recycle['yield'].items():
            message += f"- {item}: {amount}   "
        await socket.send_team_message(message)
    else:
        await socket.send_team_message(f"No recycling info found for '{item_query}'.")

# Modify the main function and chat event listener
async def main():
    try:
        options = CommandOptions(prefix="!") # Use whatever prefix you want here
        print("Connecting to Rust server...")
        await socket.connect() 
        print("Connected successfully!")

        await socket.send_team_message("Bot is online")

        @ChatEvent(server_details)
        async def chat(event: ChatEventPayload):
            print(f"{event.message.name}: {event.message.message}")
            
            # Check if the message is a command
            if event.message.message.startswith(options.prefix):
                parts = event.message.message[len(options.prefix):].split()
                command_name = parts[0].lower()
                args = parts[1:]
                
                if command_name in commands:
                    # Create a ChatCommandTime instance
                    print(event.message)
                    command_time = ChatCommandTime(
                        formatted_time=event.message.time,
                        raw_time=event.message.time
                    )
                    
                    # Create a ChatCommand instance with the correct parameters
                    command = ChatCommand(
                        sender_name=event.message.name,
                        sender_steam_id=event.message.steam_id,
                        time=command_time,
                        command=command_name,
                        args=args
                    )
                    await commands[command_name](command)
                else:
                    await socket.send_team_message(f"Unknown command: {command_name}")

        await socket.hang()
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())





import requests
import json
import asyncio
from rustplus import RustSocket, ServerDetails, Command, ChatCommand, CommandOptions

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
socket = RustSocket(server_details)

@Command(server_details,  aliases=['promote', 'lead', 'leader'])
async def promote(command : ChatCommand): 
    sender_steam_id = command.sender_steam_id
    await socket.promote_to_team_leader(sender_steam_id)
    await socket.send_team_message(f"Promoted {sender_steam_id} to team leader")
    
@Command(server_details,  aliases=['info', 'pop', 'serverinfo'])
async def info(command : ChatCommand): 

        
    rustinfo = await socket.get_info()
    await socket.send_team_message(f"Server Info:")
    await socket.send_team_message(f"URL: {rustinfo.url}")
    await socket.send_team_message(f"Name: {rustinfo.name}")
    await socket.send_team_message(f"Map: {rustinfo.map}")
    await socket.send_team_message(f"Size: {rustinfo.size}")
    await socket.send_team_message(f"Players: {rustinfo.players}")
    await socket.send_team_message(f"Max Players: {rustinfo.max_players}")
    await socket.send_team_message(f"Queued Players: {rustinfo.queued_players}")
    await socket.send_team_message(f"Seed: {rustinfo.seed}")


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

@Command(server_details, aliases=['item'])
async def get_item(command: ChatCommand):
    _, *args = command.message.split()
    if not args:
        await socket.send_team_message("Please provide an item name or ID.")
        return
    
    item_query = ' '.join(args)
    params = {'name': {'CONTAINS': item_query}}
    data = await api_request('items', params)
    
    if data and data['items']:
        item = data['items'][0]
        message = f"Item: {item['name']} (ID: {item['id']})\n"
        message += f"Stack size: {item['stack_size']}, Despawn time: {item['despawn_time']}s\n"
        message += f"Projectile weapon: {item['is_projectile_weapon']}, Melee weapon: {item['is_melee_weapon']}\n"
        message += f"Deployable: {item['is_deployable']}, Consumable: {item['is_consumable']}"
        await socket.send_team_message(message)
    else:
        await socket.send_team_message(f"No item found matching '{item_query}'.")

@Command(server_details, aliases=['craft'])
async def get_craft(command: ChatCommand):
    _, *args = command.message.split()
    if not args:
        await socket.send_team_message("Please provide an item name to get crafting info.")
        return
    
    item_query = ' '.join(args)
    params = {'result_item': {'CONTAINS': item_query}}
    data = await api_request('craft', params)
    
    if data and data['recipes']:
        recipe = data['recipes'][0]
        message = f"Crafting recipe for {recipe['result_item']} (x{recipe['result_amount']}):\n"
        for ingredient, amount in recipe['ingredients'].items():
            message += f"- {ingredient}: {amount}\n"
        await socket.send_team_message(message)
    else:
        await socket.send_team_message(f"No crafting recipe found for '{item_query}'.")

@Command(server_details, aliases=['durability'])
async def get_durability(command: ChatCommand):
    _, *args = command.message.split()
    if not args:
        await socket.send_team_message("Please provide an item name to get durability info.")
        return
    
    item_query = ' '.join(args)
    params = {'tool': {'CONTAINS': item_query}}
    data = await api_request('durability', params)
    
    if data and data['durability']:
        dur = data['durability'][0]
        message = f"Durability info for {dur['tool']}:\n"
        message += f"Type: {dur['durability_type']}, Category: {dur['category']}\n"
        message += f"Quantity: {dur['quantity']}, Time: {dur['time']}s\n"
        message += f"Fuel: {dur['fuel']}, Sulfur: {dur['sulfur']}"
        await socket.send_team_message(message)
    else:
        await socket.send_team_message(f"No durability info found for '{item_query}'.")

@Command(server_details, aliases=['loot'])
async def get_loot(command: ChatCommand):
    _, *args = command.message.split()
    if not args:
        await socket.send_team_message("Please provide a container name to get loot info.")
        return
    
    container_query = ' '.join(args)
    params = {'container': {'EQUALS': container_query}}
    data = await api_request('loot', params)
    
    if data and data['loot']:
        message = f"Loot table for {container_query}:\n"
        for item in data['loot'][:5]:  # Limit to 5 items to avoid long messages
            message += f"- {item['item']}: {item['chance']}% chance, Amount: {item['amount']}\n"
        await socket.send_team_message(message)
    else:
        await socket.send_team_message(f"No loot info found for '{container_query}'.")

@Command(server_details, aliases=['recycle'])
async def get_recycle(command: ChatCommand):
    _, *args = command.message.split()
    if not args:
        await socket.send_team_message("Please provide an item name to get recycling info.")
        return
    
    item_query = ' '.join(args)
    params = {'recycler_name': {'CONTAINS': item_query}}
    data = await api_request('recycle', params)
    
    if data and data['recycle']:
        recycle = data['recycle'][0]
        message = f"Recycling info for {recycle['recycler_name']}:\n"
        message += f"Efficiency: {recycle['efficiency']}%\n"
        message += "Yield:\n"
        for item, amount in recycle['yield'].items():
            message += f"- {item}: {amount}\n"
        await socket.send_team_message(message)
    else:
        await socket.send_team_message(f"No recycling info found for '{item_query}'.")

# Add the following code at the end of the file

async def main():
    try:
        options = CommandOptions(prefix="!") # Use whatever prefix you want here
        print("Connecting to Rust server...")
        await socket.connect() 
        print("Connected successfully!")


        await socket.send_team_message("Bot is online")

        chat = await socket.get_team_chat()

        for message in chat:
            print(message.message)

        
        @Command(server_details)
        async def hi(command : ChatCommand): 
            await socket.send_team_message(f"Hi, {command.sender_name}")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await socket.disconnect()
        print("Disconnected from Rust server.")

if __name__ == "__main__":
    asyncio.run(main())





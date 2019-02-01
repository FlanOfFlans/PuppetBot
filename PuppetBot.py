import discord
import re

print("Launching PuppetBot. This may take a second...")

client = discord.Client()

is_ready = False
home_server = None
output = None
token = None
puppet_master_ids = []
ignore_ids = []
prefix = "pb!"
prefix_been_set = False

config_file = open("PuppetConfig.txt", 'r') #todo: make this a cli argument

#we do this here, because other config options require the bot to be logged in already,
#but to log in, we need a token.

config_lines = config_file.read().split("\n")
for line in config_lines:
    if line.startswith("token:"):

        if token != None:
            raise RuntimeError("Multiple tokens defined in PuppetConfig.txt!")

        token = line.split(":")[1] #still everything after first colon

pm_regex = None
say_regex = None



async def post(channel, content):
    await client.send_message(channel, u"\u200B" + content)

@client.event
async def on_ready():
    #yes, globals are largely bad, but they seem unavoidable here.
    global is_ready
    global home_server
    global output
    global token
    global puppet_master_ids
    global ignore_ids
    global prefix
    global prefix_been_set
    global pm_regex
    global say_regex
    ignore_ids.append(client.user.id) 
    for line in config_lines:
        if line == "": #ignore blank lines
            continue
        if line[0] == '#': #marks a comment
            continue


        elif line.startswith("server:"):
            
            if home_server != None: #attempting to redefine server
                raise RuntimeError("Multiple home servers defined in PuppetConfig.txt!")
            
            else:
                
                server_id = line.split(":")[1] #take everything after the first colon
                home_server = client.get_server(server_id) 
                if home_server == None: #server not found
                    raise RuntimeError("No server found with ID " + server_id + ". Is the bot in this server?")


        elif line.startswith("home_channel:"):
            if output != None: #attempting to redefine home channel
                raise RuntimeError("Multiple home channels defined in PuppetConfig.txt!")

            else:

                channel_id = line.split(":")[1] #take everything after the first colon
                output = home_server.get_channel(channel_id)
                if output == None: #channel not found
                    raise RuntimeError("No channel found with ID " + channel_id + ". Does the bot have access to this channel?")


        elif line.startswith("master:"):
            #note we do not check if this is already defined; multiple masters are allowed!
            #we also don't throw on invalid ids; members come and go, an invalid id may later become valid,
            #and we don't ever need an actual reference to the puppet master

            master_id = line.split(":")[1] #everything after first colon
            
            if  master_id in ignore_ids:
                raise RuntimeError("User with ID " + master_id + " is both a puppet master and ignored, which isn't possible.")
            
            if home_server.get_member(master_id) == None:
                #we do, however, warn the host; they may have made a typo somewhere.
                print("Warning: No member in home server with ID " + master_id + ". This is not necessarily a problem.")
                
            puppet_master_ids.append(master_id)


        elif line.startswith("ignore:"):

            ignore_id = line.split(":")[1] #everything after first colon
            
            if ignore_id in puppet_master_ids:
                raise RuntimeError("User with ID " + ignore_id + " is both a puppet master and ignored, which isn't possible.")
            
            if home_server.get_member(ignore_id) == None:
                print("Warning: No member in home server with ID " + ignore_id + ". This is not necessarily a problem.")

            ignore_ids.append(ignore_id)


        elif line.startswith("prefix:"):
            if prefix_been_set == True:
                raise RuntimeError("Multiple prefixes defined in PuppetConfig.txt!")
            
            prefix_been_set = True
            prefix = line.split(":")[1] #everything after first colon


        elif line.startswith("token:"): pass #we processed this earlier


        else:
            raise RuntimeError("Malformed PuppetConfig.txt! Invalid line:\n" + line)


    if home_server == None:
        raise RuntimeError("A home server must be defined in PuppetConfig.txt!")
    if output == None:
        raise RuntimeError("A home channel must be defined in PuppetConfig.txt!")
    if token == None:
        raise RuntimeError("A token must be defined in PuppetConfig.txt!")
    if len(puppet_master_ids) == 0:
        raise RuntimeError("At least one puppet master must be defined in PuppetConfig.txt!")

    say_regex = re.compile("^" + prefix + "say ([^ ]+) (.*)$")
    pm_regex = re.compile("^" + prefix + "pm \"(.+)\" (.+)$")

    is_ready = True
    print("PuppetBot is ready for use!")



@client.event
async def on_message(message):
    if not is_ready:
        return
    
    if message.author.id in ignore_ids:
        return #don't respond to ignored users

    if message.content[0] == u"\u200B":
        return #don't respond to other puppetbots; all puppetbot messages are prefixed with ASCII null
    
    if message.author.id in puppet_master_ids:
        if message.content.startswith(prefix + "pm"):
            match = re.match(pm_regex, message.content)
            if match != None:
                target = home_server.get_member_named(match.group(1))
                if target == None:
                    await post(message.channel, "Invalid target.")
                else:
                    await post(target, match.group(2))

        
        if message.content.startswith(prefix + "say"):
            match = re.match(say_regex, message.content)
            if match != None:
                
                for channel in home_server.channels:
                    if channel.name == match.group(1):
                        target = channel
                        break

                #this else belongs to for, NOT if
                else:
                    post(message.channel, "Invalid channel.")
                    return
                
                output_message = match.group(2)
                await post(target, output_message)

    if message.server == None: #If there's no server, it must be a PM
        await post(output, "I've been PM'd by " + message.author.name + "!\n" + message.content)

    #This is an elif, because we only need to report once if somebody pings in a PM.
    elif client.user in message.mentions:
        await post(output, "I've been pinged by " + message.author.name + "!\n" + message.content)


client.run(token)

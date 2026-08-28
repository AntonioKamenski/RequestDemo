from twitchAPI.chat import Chat, EventData, ChatMessage
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch
from queryMatching import find_best_match, is_extreme
from queue_utils import format_queue, is_song_in_queue
import asyncio
import os
import json


from threadingShared import bot_stop_event

import threadingShared

from main import (
    df,
    commands,
    TARGET_CHANNEL,
    displayName,
    maxRequestsPerUser,
    songQueueFilePath,
    banned_df,
    queryAccuracy,
    TOKEN_FILE,
    MainWindow,
    APP_ID,
    APP_SECRET,
)

USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]

class SongQueue(list):
    def save(self):
        SongRequest.save()

    @classmethod
    def load(cls):
        return cls(SongRequest.load())


class SongRequest:
    def __init__(self, songName, artist, extreme, alternate, user, gameVersions):
        self.songName = songName
        self.artist = artist
        self.user = user
        self.extreme = extreme
        self.alternate = alternate
        self.gameVersions = gameVersions

    def SongRequest(songName, artist,  extreme, alternate, user, gameVersions):
        songName = songName
        artist = artist
        extreme = extreme
        user = user
        alternate = alternate
        gameVersions = gameVersions
        return SongRequest(songName, artist, extreme, alternate, user, gameVersions)

    def getRequestAsString(self):
        alternate = f" ({self.alternate})"
        return f"{self.songName} - {self.artist}{' (Extreme)' if self.extreme else ''}{alternate if (self.alternate != '-' and self.alternate != 'Extreme') else ''}"

    @staticmethod
    def save():
        queue_data = [
            {
                'song_name': request.songName,
                'artist': request.artist,
                'extreme': request.extreme,
                'alternate': request.alternate,
                'user_name': request.user.display_name,
                'game_versions': request.gameVersions,
            }
            for request in songQueue
        ]

        with open(songQueueFilePath, 'w', encoding='utf-8') as file:
            json.dump(queue_data, file, indent=2)

    @staticmethod
    def load():
        song_requests = []
        file_path = songQueueFilePath
        if not os.path.exists(file_path):
            print("No save file found.")
            return song_requests
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                queue_data = json.load(file)

            for request_data in queue_data:
                user = type('User', (), {
                    'display_name': request_data['user_name']
                })()
                song_requests.append(
                    SongRequest(
                        request_data['song_name'],
                        request_data['artist'],
                        request_data['extreme'],
                        request_data['alternate'],
                        user,
                        request_data['game_versions'],
                    )
                )
        except Exception as e:
            print(f"Load error: {e}")
        return song_requests

songQueue = SongQueue.load()

def getGameVersions(index):
    gameVersions = "("
    gameVersions = gameVersions + str(df['game'].iloc[index])
    if df['JD+'].iloc[index] == True and df['game'].iloc[index] != 'JD+':
        gameVersions = gameVersions + "/JD+)"
    else:
        gameVersions = gameVersions + ")"
    return gameVersions

def queueFormatting(songQueueOriginal):
    songQueueForm = []
    if len(songQueueOriginal) == 0:
        return "Queue is empty!"
    for song in songQueueOriginal:
        songQueueForm.append(song)

    message = f"Queue: #1 \"{songQueueForm[0].getRequestAsString()}\""
    songQueueForm.remove(songQueueForm[0])
    counter = 2
    
    for song in songQueueForm:
        message += f", #{counter} \"{song.getRequestAsString()}\""
        counter += 1

    message += "."
    return message

async def on_ready(ready_event: EventData, window: MainWindow):
    threadingShared.botIsRunning = True
    await ready_event.chat.join_room(TARGET_CHANNEL)
    print(f'Successfully connected to {TARGET_CHANNEL}\'s chat!')
    window.status_signal.emit(f'Successfully connected to {TARGET_CHANNEL}\'s chat!')
    print('Commands are:')
    for command in commands:
        print(f'{command}')
    await ready_event.chat.send_message(room=TARGET_CHANNEL, text=f'Successfully connected to {TARGET_CHANNEL}\'s chat!')

async def on_message(msg: ChatMessage):
    if msg.text[0:3] == '!sr':
        if threadingShared.adminMode:
            if not msg.user.mod and not msg.user.display_name == displayName:
                await msg.chat.send_message(room=TARGET_CHANNEL, text=threadingShared.customMessage)
                return
        userRequests = 0
        for song in songQueue:
            if song.user.display_name == msg.user.display_name:
                userRequests += 1
        if threadingShared.streamEnding == 1:
            await msg.chat.send_message(room=TARGET_CHANNEL, text=f'Stream is ending, remember your request for next stream!')
        elif userRequests > maxRequestsPerUser-1:
            await msg.chat.send_message(room=TARGET_CHANNEL, text=f'You have reached the maximum number of song requests at this time!')
        elif len(msg.text) > 4:
            message = msg.text[4:].lower()
            extreme, message = is_extreme(message)
            song = find_best_match(message, df, extreme)
            inQueue, requester = is_song_in_queue(song['row_index'], df, songQueue)
            if inQueue:
                await msg.chat.send_message(room=TARGET_CHANNEL, text=f'This song is already in the queue, {requester} already requested this song!')
                return
            for _, banned_row in banned_df.iterrows():
                if banned_row['songName'] == df['songName'].iloc[song['row_index']] and banned_row['alternate'] == df['alternate'].iloc[song['row_index']] and not threadingShared.adminMode:
                    await msg.chat.send_message(room=TARGET_CHANNEL, text=f'Song \"{df["songName"].iloc[song["row_index"]]}\" {"(Extreme)" if df["extreme"].iloc[song["row_index"]] else ""} is banned!')
                    return  
            if song['similarity'] < queryAccuracy:
                await msg.chat.send_message(room=TARGET_CHANNEL, text=f'Couldn\'t find any song to match your request, check your spelling and try again!')
            else:
                songObject = SongRequest(df['songName'].iloc[song['row_index']], df['ContributingArtists'].iloc[song['row_index']], df['extreme'].iloc[song['row_index']], df['alternate'].iloc[song['row_index']], msg.user, getGameVersions(song['row_index']))   
                songQueue.append(songObject)
                await msg.chat.send_message(room=TARGET_CHANNEL, text=f'Added song \"{songObject.getRequestAsString()}\" to queue!')
        else:
            await msg.chat.send_message(room=TARGET_CHANNEL, text=f'Invalid song name!')
    SongRequest.save()

    if msg.text[0:6] == '!queue' and (msg.user.display_name == displayName or msg.user.mod or msg.user.vip):
        if len(songQueue) == 0:
            await msg.chat.send_message(room=TARGET_CHANNEL, text=f'Queue is empty!')
        
        else:
            await msg.chat.send_message(room=TARGET_CHANNEL, text=format_queue(songQueue))
    

    if msg.text[0:5] == '!next' and (msg.user.display_name == displayName or msg.user.mod or msg.user.vip):
        if len(songQueue) == 0:
            await msg.chat.send_message(room=TARGET_CHANNEL, text=f'No songs in queue!')

        elif len(songQueue) == 1:
            currentSong = songQueue[0]
            await msg.chat.send_message(room=TARGET_CHANNEL, text=f'Song \"{currentSong.songName}\" was played. No more songs in queue!')
            songQueue.clear()
        else:
            currentSong = songQueue[0]
            songQueue.remove(songQueue[0])
            await msg.chat.send_message(room=TARGET_CHANNEL, text=f'Song \"{currentSong.songName}\" was played. \"{songQueue[0].songName}\" is up next!')
        SongRequest.save()
    
    if msg.text[0:6] == '!clear' and msg.user.display_name == displayName:
        if len(songQueue) == 0:
            await msg.chat.send_message(room=TARGET_CHANNEL, text=f'Queue is already empty!')
        else:
            songQueue.clear()
            await msg.chat.send_message(room=TARGET_CHANNEL, text=f"Cleared queue!")
        SongRequest.save()
            

    if msg.text[0:7] == '!remove' and (msg.user.display_name == displayName or msg.user.mod):
        try:
            index = int(msg.text[8:])-1

            if index >= len(songQueue) or index < 0:
                await msg.chat.send_message(room=TARGET_CHANNEL, text=f'No song at that number in the queue!')
            else:
                song = songQueue[index]
                songQueue.remove(songQueue[index])
                await msg.chat.send_message(room=TARGET_CHANNEL, text=f'Removed song \"{song.getRequestAsString()}\" from queue!')
        except:
            await msg.chat.send_message(room=TARGET_CHANNEL, text=f'Invalid song number!')
        SongRequest.save()

    if msg.text[0:5] == '!oops':
        foundSong = False
        for song in reversed(songQueue):
            if song.user.display_name == msg.user.display_name:
                await msg.chat.send_message(room=TARGET_CHANNEL, text=f'Removed song \"{song.getRequestAsString()}\" from queue!')
                songQueue.remove(song)
                foundSong = True
                break
        if not foundSong:
            await msg.chat.send_message(room=TARGET_CHANNEL, text=f'You have no song requests in the queue!')
        SongRequest.save()

    if msg.text[0:4] == '!end' and msg.user.display_name == displayName:
        await msg.chat.send_message(room=TARGET_CHANNEL, text=f'No more song requests will be taken today!')
        streamEnding = True

async def run_async(window: MainWindow):
    threadingShared.state.twitch = await Twitch(APP_ID, APP_SECRET)
    
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            data = json.load(f)
        token, refresh_token = data['token'], data['refresh_token']
        await threadingShared.state.twitch.set_user_authentication(token, USER_SCOPE, refresh_token)
    else:
        auth = UserAuthenticator(threadingShared.state.twitch, USER_SCOPE)
        token, refresh_token = await auth.authenticate()
        await threadingShared.state.twitch.set_user_authentication(token, USER_SCOPE, refresh_token)
        with open(TOKEN_FILE, 'w') as f:
            json.dump({'token': token, 'refresh_token': refresh_token}, f)

    chat = await Chat(threadingShared.state.twitch)
    threadingShared.state.chat = chat
    
    async def ready_handler(e):
        await on_ready(e, window)
    
    chat.register_event(ChatEvent.READY, ready_handler)
    chat.register_event(ChatEvent.MESSAGE, on_message)
    
    print("Starting Twitch chat...")
    chat.start()

    try:
        while not bot_stop_event.is_set():
            await asyncio.sleep(0.1)

        print("\nStopping...")

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        if chat is not None:
            try:
                chat.stop()
            except RuntimeError:
                pass

        if threadingShared.state.twitch is not None:
            await threadingShared.state.twitch.close()

        window.status_signal.emit(f'Disconnected from {TARGET_CHANNEL}\'s chat!')
        threadingShared.botIsRunning = False

        print("Cleanup complete")

def run(window: MainWindow):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_async(window))
    finally:
        loop.close()
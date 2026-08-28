def format_queue(song_queue):
    if not song_queue:
        return "Queue is empty!"

    lines = [
        f"#{index} {song.getRequestAsString()} "
        f"(Difficulty: {song.difficulty}) requested by "
        f"{song.user.display_name} {song.gameVersions}"
        for index, song in enumerate(song_queue, start=1)
    ]
    return "\n".join(lines)


def is_song_in_queue(index, songs, song_queue):
    if index < 0 or index >= len(songs):
        return False, None

    song = songs.iloc[index]
    for queued_song in song_queue:
        if (
            queued_song.songName == song.songName
            and queued_song.alternate == song.alternate
        ):
            return True, queued_song.user.display_name

    return False, None

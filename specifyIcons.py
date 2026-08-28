import pandas as pd

loadedCsv = pd.read_csv('resources/songLists/JustDanceSongsFull.csv')

print(loadedCsv.info())

games = loadedCsv['OA.'].unique()

dict = {}
for game in games:
    print(f"Enter link for game {game}:")
    link = input()

    dict[game] = link

print('saving dict to file...')
with open('gameLinks.txt', 'w') as f:
    for key, value in dict.items():
        f.write(f"{key}: {value}\n")

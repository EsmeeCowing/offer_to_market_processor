import json
import csv

path_to_unprocessed_file = "unprocessedCounties.csv"
path_to_processed_file = "uscounties.txt"

def main():
    with open(path_to_unprocessed_file, 'r') as file:
        reader = csv.DictReader(file)
        items = [row["County or equivalent"] for row in reader]

    # with open(path_to_unprocessed_file, 'r') as file:
    #     content = file.read().strip()
    #     items = content.split('    ')
    #     items = [item.strip() for item in items]
    
    unduplicatedItems = []
    for item in items:
        if item not in unduplicatedItems:
            unduplicatedItems.append(item)

     
    with open(path_to_processed_file, 'w') as file:
        file.write('    '.join(unduplicatedItems))

    

if __name__ == '__main__':
    main()
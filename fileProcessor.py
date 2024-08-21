import json

def main():
    state_codes = []
    with open('StateCodes.txt', 'r') as file:
        content = file.read().strip()
        state_codes = content.split(',')
        state_codes = [state_code.strip() for state_code in state_codes] 
     
    with open('USStateCodes.txt', 'w') as file:
        file.write('    '.join(state_codes))

    

if __name__ == '__main__':
    main()
import os

# working directory skal være denne mappe
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

def create_folders():
    # lav mapper, skip hvis de allerede findes
    os.makedirs('src\Data\\', exist_ok=True)
    os.makedirs('src\Resultater\\', exist_ok=True)
    
    
if __name__ == '__main__':
    create_folders()
    print('Opsætning er færdig :)')
    print('1. Læg data i src/Data.')
    print('2. Kør algoritmen ved at åbne run.py og tryk kør.')
    print('3. Resultater ligger i src/Resultater')
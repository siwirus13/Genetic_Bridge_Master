import pandas as pd
import matplotlib.pyplot as plt
import io

# Dane dla pierwszej metody (pierwszy CSV)
data_method1 = """Deal File,Contract,Declarer,Trump,Opening Lead,Declarer Tricks,Result,Over/Under Tricks,Best Fitness,Runtime (s)
utils/deals\\1D.dat,1D,S,D,KD,6,DOWN,1,-,1.96
utils/deals\\2C.dat,2C,S,C,QH,8,MADE,0,-,2.08
utils/deals\\3C.dat,3C,S,C,6D,9,MADE,0,-,1.88
utils/deals\\4H.dat,4H,S,H,TH,8,DOWN,2,-,1.95
utils/deals\\4S.dat,4S,S,S,KC,5,DOWN,5,-,1.97
utils/deals\\5C.dat,5C,S,C,3C,6,DOWN,5,-,1.97
utils/deals\\5D.dat,5D,S,D,TC,8,DOWN,3,-,1.99
utils/deals\\6D.dat,6D,S,D,2C,9,DOWN,3,-,1.81
utils/deals\\6H.dat,6H,S,H,TD,11,DOWN,1,-,1.72
utils/deals\\7C.dat,7C,S,C,8H,13,MADE,0,-,1.82
"""

# Dane dla drugiej metody (drugi CSV)
data_method2 = """Deal File,Contract,Declarer,Trump,Opening Lead,Declarer Tricks,Result,Over/Under Tricks,Best Fitness,Runtime (s)
utils/deals\\1D.json,1D,S,D,KD,9,MADE,2,178.09,37.30
utils/deals\\2C.json,2C,S,C,QH,9,MADE,1,174.31,40.65
utils/deals\\3C.json,3C,S,C,6D,7,DOWN,2,43.04,44.91
utils/deals\\4H.json,4H,S,H,TH,10,MADE,0,173.46,47.48
utils/deals\\4S.json,4S,S,S,KC,13,MADE,3,230.80,49.79
utils/deals\\5C.json,5C,S,C,3C,12,MADE,1,170.36,49.25
utils/deals\\5D.json,5D,S,D,TC,12,MADE,1,200.27,51.65
utils/deals\\6D.json,6D,S,D,2C,12,MADE,0,165.86,49.65
utils/deals\\6H.json,6H,S,H,TD,13,MADE,1,201.17,46.22
utils/deals\\7C.json,7C,S,C,8H,13,MADE,0,179.90,45.52
"""

# Wczytaj dane do ramek danych pandas
df1 = pd.read_csv(io.StringIO(data_method1))
df2 = pd.read_csv(io.StringIO(data_method2))

# Upewnij się, że kolumna 'Deal File' jest używana jako etykiety dla osi X
# Możemy uprościć etykiety, biorąc tylko nazwę pliku
df1['Deal Name'] = df1['Deal File'].apply(lambda x: x.split('\\')[-1].split('.')[0])
df2['Deal Name'] = df2['Deal File'].apply(lambda x: x.split('\\')[-1].split('.')[0])

# Funkcja do wyodrębniania liczby lew potrzebnych do ugrania kontraktu
def get_required_tricks(contract):
    try:
        # Kontrakt jest np. '1D', '2C', więc bierzemy pierwszą cyfrę i dodajemy 6
        return int(contract[0]) + 6
    except (ValueError, IndexError):
        return None # Obsługa błędów, jeśli format kontraktu jest nieoczekiwany

# Dodaj kolumnę z wymaganą liczbą lew do obu ramek danych
df1['Required Tricks'] = df1['Contract'].apply(get_required_tricks)
df2['Required Tricks'] = df2['Contract'].apply(get_required_tricks)

# Sortowanie danych według 'Deal Name', aby zapewnić spójność na wykresach
df1 = df1.sort_values(by='Deal Name').reset_index(drop=True)
df2 = df2.sort_values(by='Deal Name').reset_index(drop=True)


# --- Wykres porównujący czasy wykonania (Runtime) ---
plt.figure(figsize=(12, 6))
plt.plot(df1['Deal Name'], df1['Runtime (s)'], marker='o', label='CPLEX SOLVER')
plt.plot(df2['Deal Name'], df2['Runtime (s)'], marker='x', color = 'g',  label='GA SOLVER')
plt.xlabel('Nazwa Pliku Danych')
plt.ylabel('Czas wykonania (s)')
plt.title('Porównanie Czasów Wykonania dla Dwóch Metod')
plt.xticks(rotation=45, ha='right')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()

# --- Wykres porównujący liczbę zdobytych lew (Declarer Tricks) ---
plt.figure(figsize=(12, 6))
plt.plot(df1['Deal Name'], df1['Declarer Tricks'], marker='o', label='CPLEX SOLVER')
plt.plot(df2['Deal Name'], df2['Declarer Tricks'], marker='x', color = 'g', label='GA SOLVER')

# Dodajemy punkty z wymaganą liczbą lew
# Zakładamy, że Required Tricks są takie same dla obu metod dla danego kontraktu
plt.scatter(df1['Deal Name'], df1['Required Tricks'], color='red', marker='D', s=100, label='Wymagane do kontraktu') # 'D' to symbol diamentu
plt.xlabel('Nazwa Pliku Danych')
plt.ylabel('Liczba Zdobytych Lew')
plt.title('Porównanie Liczby Zdobytych Lew oraz Wymaganych Lew do Kontraktu')
plt.xticks(rotation=45, ha='right')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()
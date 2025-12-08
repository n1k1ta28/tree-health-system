# 🌲 Miškorius

Dronais ir dirbtiniu intelektu grįsta miškų priežiūros sistema

Miškorius – tai inovatyvi internetinė sistema, kuri padeda miškų savininkams ir valdytojams efektyviai stebėti savo miškus. Naudojant dronų darytas nuotraukas ir dirbtinio intelekto modelį, sistema automatiškai aptinka sudžiūvusius ar pažeistus medžius, nustato jų tikslią vietą ir pateikia struktūruotą informaciją interaktyviame žemėlapyje.

Projektas sukurtas laikantis Scrum metodologijos, įgyvendintas per kelis sprintus, apimantis rinkos analizę, tyrimus, prototipų kūrimą ir galutinio MVP realizavimą.

## 📌 Projekto tikslas

Sukurti išmanią miškų stebėjimo sistemą, kuri:
- Automatiškai atpažintų išdžiūvusius ar sergančius medžius iš dronų darytų nuotraukų.
- Sumažintų miško priežiūrai reikalingą laiką bei žmogiškąsias klaidas.
- Padėtų greitai reaguoti į pavojingus miško būklės pokyčius.
- Suteiktų galimybę mišką valdyti nuotoliniu būdu.

## 🚀 Pagrindinės funkcijos

- DI modelis džiūstančių medžių aptikimui
- Interaktyvus žemėlapis su pažymėtomis medžių koordinatėmis
- Miško sklypų valdymas
- Nuotraukų įkėlimas ir analizavimas
- Naudotojų autentifikacija (el. paštas, Google prisijungimas)
- Sisteminių pranešimų el. paštu siuntimas (atkūrimo, patvirtinimo pranešimai)
- Prenumeratos ir vienkartinių užsakymų pasirinkimas
- Darbuotojų užsakymų, patikrų ir raportų valdymas

## 🧠 Naudojamos technologijos

Back-end
- Django (Python)
- PostgreSQL – duomenų bazė
- DigitalOcean – serveriai ir DI talpinimas
- Leaflet.js – interaktyviam žemėlapiui

Dirbtinis intelektas
- CNN/kompiuterinės regos modeliai nudžiūvusių medžių aptikimui
- Modelių optimizavimas per kelis sprintus

Front-end
- HTML / CSS / JS
- Interaktyvūs žemėlapiai ir naudotojo sąsaja

Dronų įranga
- DJI dronai su RTK GPS aukštam tikslumui

## 🏗 Sistemos architektūra (santrauka)
- Naudotojai įkelia drono nuotraukas į sistemą.
- DI modelis atpažįsta pažeistus medžius ir grąžina koordinacijas.
- Rezultatai išsaugomi PostgreSQL DB.
- Duomenys vizualizuojami Leaflet žemėlapyje.
- Naudotojui pateikiamas raportas bei galimybė užsakyti papildomas paslaugas.

## 🧪 Tyrimai ir rinkos analizė
Projektas remiasi vartotojų balso tyrimu:
- 96% miško valdytojų susiduria su džiūstančių medžių problema
- 93% juos pastebi per vėlai
- 87% būtų pasirengę naudotis tokia sistema
- Dauguma valdytojų turi 80–150 ha ar didesnius plotus
- Miško savininkai norėtų gauti atnaujinimus kartą per mėnesį arba pusmetį
- Tikslinis segmentas – didelio ploto miškų savininkai ir profesionalūs miškininkai.

## 📅 Vystymas pagal Scrum

Projektas įgyvendintas per 6 sprintus, kuriuose sukurta:
-Vartotojų registracija, prisijungimas, Google auth
- Miškų pridėjimas, nuotraukų galerijos, žemėlapiai
- DI modelio versijos: pradinė → patobulinta → galutinė
- Užsakymų, patikrų ir prenumeratų sistema
- El. laiškų šablonai (slaptažodžio atkūrimas, el. pašto patvirtinimas)
- Mokėjimų simuliacija
- Pažeistų medžių žymėjimas ir sutvarkymo ataskaitos

## 🧑‍🤝‍🧑 Komanda

| Vardas |	Sritis |	Studijų programa |
| --- | --- | ---- |
|Justė Baltrušytė |	Finansai |	V FBF-3 |
| Aurelija Vaitkutė |	Back-end / Front-end |	IFK-2 |
| Domas Unikas |	DI |	IFD-2 |
| Nikita Kisialeuski |	Back-end / Front-end |	IFD-2 |
| Titas Sukackas |	Rinkos analizė / Ekonomika |	V EBV-2 |
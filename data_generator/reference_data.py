# -*- coding: utf-8 -*-
"""
reference_data.py
=================
Reference pools for the synthetic Indian crime-network dataset.

IMPORTANT / ETHICS
------------------
Every person, organisation, phone number, account and incident produced from
this file is SYNTHETIC. Names are assembled by sampling culturally-authentic
first-name and surname pools; they are NOT drawn from real criminal records and
any resemblance to a living person is coincidental. Geography, police-station
naming conventions and statute sections are real so that the data *behaves*
realistically for NLP / graph analytics, but no real individual is implicated.
"""

# ---------------------------------------------------------------------------
# 1. NAME POOLS  (region -> male / female given names + surnames)
# ---------------------------------------------------------------------------

NAME_POOLS = {
    "hindi_belt": {  # UP, MP, Delhi, Haryana, Uttarakhand
        "m": ["Ramesh", "Suresh", "Mahesh", "Rajesh", "Dinesh", "Mukesh", "Naresh",
              "Vinod", "Pramod", "Anil", "Sunil", "Ashok", "Vijay", "Ajay", "Sanjay",
              "Manoj", "Arun", "Rakesh", "Deepak", "Prakash", "Jitendra", "Satish",
              "Yogendra", "Bhupendra", "Devendra", "Shailendra", "Kuldeep", "Pradeep",
              "Sandeep", "Randhir", "Balbir", "Rambabu", "Shyamlal",
              "Girdhari", "Munna", "Om Prakash", "Har Prasad", "Triloki",
              "Jagdish", "Netrapal", "Udaiveer", "Hariom", "Chandrabhan", "Lekhraj"],
        "f": ["Sunita", "Anita", "Kavita", "Savita", "Rekha", "Seema", "Meena",
              "Poonam", "Pushpa", "Kamla", "Shanti", "Urmila", "Nirmala", "Sarita",
              "Rajni", "Neelam", "Shakuntala", "Ramkali", "Vidyawati",
              "Preeti", "Archana", "Rachna", "Sudha", "Manju"],
        "sur": ["Yadav", "Sharma", "Verma", "Singh", "Tiwari", "Mishra", "Pandey",
                "Chauhan", "Rathore", "Gupta", "Jaiswal", "Kashyap", "Nishad",
                "Prajapati", "Kushwaha", "Maurya", "Saini", "Bhardwaj", "Dubey",
                "Shukla", "Tomar", "Sengar", "Bhadauria", "Nagar", "Solanki",
                "Rajput", "Thakur", "Baghel", "Dixit", "Awasthi", "Srivastava"],
    },
    "punjabi": {
        "m": ["Gurpreet", "Jagdeep", "Harjinder", "Sukhwinder", "Balwinder", "Manpreet",
              "Amarjit", "Ranjit", "Tarsem", "Jaswant", "Kulwant", "Satnam", "Harbhajan",
              "Lakhwinder", "Baljinder", "Davinder", "Paramjit", "Gurmeet", "Jarnail",
              "Sukhdev", "Nirmal", "Karamjit", "Bikramjit", "Rachhpal", "Malkiat"],
        "f": ["Harpreet", "Simranjit", "Kuldeep", "Rajwinder", "Baljit", "Jasbir",
              "Manjit", "Surinder", "Amandeep", "Navneet", "Charanjit", "Parminder"],
        "sur": ["Singh", "Sidhu", "Gill", "Dhillon", "Bajwa", "Randhawa", "Sandhu",
                "Brar", "Grewal", "Cheema", "Mann", "Aulakh", "Sekhon", "Virk",
                "Bhullar", "Toor", "Sarao", "Dhaliwal", "Bains", "Kang"],
    },
    "rajasthani": {
        "m": ["Bhanwar", "Kishan", "Gopal", "Mohan", "Hanuman", "Bhoma",
              "Ranveer", "Jagmal", "Devi Lal", "Poonam Chand",
              "Nathu", "Chhagan", "Madan", "Karni", "Bheru", "Ratan", "Sohan"],
        "f": ["Bhanwari", "Sushila", "Kesar", "Gayatri", "Bhagwati", "Mangi",
              "Sarla", "Laxmi", "Kanta", "Suman"],
        "sur": ["Rathore", "Shekhawat", "Chouhan", "Bishnoi", "Jat", "Meena", "Gurjar",
                "Sisodia", "Ranawat", "Charan", "Jhala", "Purohit", "Vyas", "Choudhary",
                "Kumawat", "Saini", "Bhati", "Godara", "Poonia", "Beniwal"],
    },
    "gujarati": {
        "m": ["Jayesh", "Nilesh", "Hitesh", "Mitesh", "Bhavesh", "Kalpesh", "Paresh",
              "Chirag", "Hardik", "Dharmesh", "Ashwin", "Ketan", "Rasik", "Bharat",
              "Kishor", "Jignesh", "Vipul", "Tushar", "Alpesh", "Divyesh"],
        "f": ["Hansa", "Jyoti", "Falguni", "Bhavna", "Rinku", "Hetal", "Nisha",
              "Vaishali", "Trupti", "Sonal"],
        "sur": ["Patel", "Shah", "Desai", "Mehta", "Joshi", "Parmar", "Chauhan",
                "Vaghela", "Solanki", "Rabari", "Thakor", "Bhatt", "Trivedi",
                "Dave", "Gohil", "Zala", "Makwana", "Prajapati", "Barot"],
    },
    "marathi": {
        "m": ["Sachin", "Nitin", "Sagar", "Ganesh", "Mangesh", "Prashant", "Nilesh",
              "Amol", "Sandip", "Vishal", "Rahul", "Swapnil", "Yogesh",
              "Dattatray", "Tanaji", "Pandurang", "Kiran", "Bhaskar"],
        "f": ["Snehal", "Priyanka", "Aarti", "Vaishnavi", "Manisha", "Shubhangi",
              "Rohini", "Smita", "Jyotsna", "Madhuri"],
        "sur": ["Shinde", "Pawar", "Jadhav", "More", "Patil", "Deshmukh", "Kadam",
                "Salunkhe", "Bhosale", "Chavan", "Gaikwad", "Sawant", "Naik",
                "Rane", "Kamble", "Mhatre", "Bhoir", "Tandel", "Dalvi", "Waghmare"],
    },
    "bengali": {
        "m": ["Sukumar", "Bikash", "Tapan", "Ranjan", "Debashish", "Anup", "Pradip",
              "Sanjib", "Ashim", "Nirmal", "Kartik", "Gautam", "Swapan", "Bimal",
              "Palash", "Sujoy", "Arindam", "Subhas", "Gopal", "Nepal"],
        "f": ["Moumita", "Rupa", "Sabitri", "Chhaya", "Aparna", "Mousumi", "Tapasi",
              "Bandana", "Sikha", "Rina"],
        "sur": ["Mondal", "Ghosh", "Das", "Sarkar", "Halder", "Biswas", "Roy",
                "Bhattacharya", "Chakraborty", "Dutta", "Pal", "Bose", "Naskar",
                "Mistry", "Adhikari", "Majumdar", "Sen", "Gayen", "Sardar", "Barman"],
    },
    "odia": {
        "m": ["Bibhuti", "Sudarshan", "Prasanna", "Jagabandhu", "Rabindra", "Sarat",
              "Trilochan", "Bhagaban", "Niranjan", "Basanta", "Akshaya"],
        "f": ["Sabita", "Pramila", "Sasmita", "Basanti", "Kuni", "Jhunu"],
        "sur": ["Sahoo", "Nayak", "Behera", "Jena", "Mohanty", "Pradhan", "Rout",
                "Swain", "Patra", "Barik", "Panda", "Dash", "Mallick", "Bhoi", "Munda"],
    },
    "tamil": {
        "m": ["Murugan", "Selvam", "Karthik", "Saravanan", "Elango", "Thangaraj",
              "Kumaresan", "Palanisamy", "Manikandan", "Vetrivel", "Anbu", "Sekar",
              "Bala", "Rajendran", "Ilango", "Mariappan", "Chinnadurai", "Arivazhagan",
              "Perumal", "Kannan", "Dhanapal", "Velu", "Ravichandran"],
        "f": ["Kalaiselvi", "Amutha", "Poongodi", "Vasanthi", "Revathi", "Malathi",
              "Jothi", "Tamilselvi", "Bhuvana", "Chitra"],
        "sur": ["Raja", "Pandian", "Nadar", "Gounder", "Thevar", "Chettiar", "Pillai",
                "Mudaliar", "Naicker", "Kurup", "Sundaram", "Subramanian",
                "Rajendran", "Muthusamy", "Palanivel", "Annadurai"],
    },
    "telugu": {
        "m": ["Venkatesh", "Srinivas", "Ramulu", "Narsimha", "Nagaraju", "Sathish",
              "Rambabu", "Chandra Shekar", "Yellaiah", "Mallesh", "Sudhakar",
              "Prabhakar", "Kondaiah", "Ravinder", "Balaraju", "Anjaiah", "Krishnaiah"],
        "f": ["Lakshmi", "Padma", "Sujatha", "Vijaya", "Aruna", "Rajitha", "Swaroopa",
              "Mangamma", "Saroja", "Kavya"],
        "sur": ["Reddy", "Naidu", "Rao", "Choudary", "Goud", "Yadav", "Gupta",
                "Varma", "Sharma", "Kumar", "Prasad", "Chowdary", "Raju", "Setty",
                "Bandari", "Mudiraj", "Nallamothu", "Kondapalli", "Vemula"],
    },
    "kannada": {
        "m": ["Basavaraj", "Mallikarjun", "Shivanna", "Ravi", "Nagesh", "Kumaraswamy",
              "Manjunath", "Prakash", "Girish", "Yallappa", "Siddaraju", "Chandru",
              "Puttaraju", "Hanumanthappa", "Veeresh", "Lokesh"],
        "f": ["Shobha", "Geetha", "Nagaratna", "Sumitra", "Bhagya", "Renuka",
              "Pushpalatha", "Chandrakala"],
        "sur": ["Gowda", "Shetty", "Hegde", "Rai", "Poojary", "Naik", "Patil",
                "Desai", "Hiremath", "Kulkarni", "Bhat", "Acharya", "Kamath",
                "Bellad", "Angadi", "Chikkanna"],
    },
    "malayali": {
        "m": ["Rajeevan", "Sudheer", "Anoop", "Vinayakan", "Shibu", "Manoj", "Biju",
              "Praveen", "Sajeev", "Unnikrishnan", "Jayan", "Sreenivasan", "Baiju",
              "Nishad", "Vipin", "Ratheesh", "Sanoop"],
        "f": ["Sindhu", "Bindu", "Remya", "Sreeja", "Anitha", "Lissy", "Deepa",
              "Sajitha", "Nimmi"],
        "sur": ["Nair", "Menon", "Pillai", "Kurup", "Warrier", "Panicker", "Namboothiri",
                "Thomas", "Mathew", "Varghese", "Joseph", "Jacob", "Nambiar",
                "Marar", "Kartha", "Achari"],
    },
    "muslim": {
        "m": ["Mohammed", "Abdul", "Imran", "Salim", "Firoz", "Javed", "Nadeem",
              "Shakeel", "Anwar", "Iqbal", "Rafiq", "Yusuf", "Sajid", "Wasim",
              "Naseer", "Zubair", "Arif", "Tanveer", "Faizan", "Rizwan", "Ashfaq",
              "Mushtaq", "Aslam", "Haroon", "Ibrahim", "Shahnawaz", "Altaf", "Sarfaraz"],
        "f": ["Shabana", "Nasreen", "Rukhsana", "Farida", "Yasmin", "Shahnaz",
              "Reshma", "Nazia", "Afsana", "Rubina"],
        "sur": ["Khan", "Ansari", "Sheikh", "Qureshi", "Siddiqui", "Pathan", "Mirza",
                "Alam", "Hussain", "Ahmed", "Rahman", "Malik", "Shaikh", "Idrisi",
                "Saifi", "Mansuri", "Chaudhary", "Baig", "Farooqui", "Zaidi"],
    },
    "christian": {
        "m": ["Anthony", "Peter", "Francis", "Xavier", "Joseph", "Michael", "Alwyn",
              "Rodney", "Savio", "Denzil", "Ronald", "Vivian"],
        "f": ["Maria", "Agnes", "Sheryl", "Delphine", "Juliet", "Clara"],
        "sur": ["Fernandes", "D'Souza", "Pereira", "Rodrigues", "Lobo", "Menezes",
                "Coutinho", "Almeida", "Gonsalves", "Pinto", "Dias", "Noronha"],
    },
    "northeast": {
        "m": ["Bikram", "Lalthanga", "Zothanpuia", "Temjen", "Nabam",
              "Techi", "Yumnam", "Kishorchandra", "Bidyananda", "Alemba"],
        "f": ["Lalrinpuii", "Mercy", "Thoibi", "Sanatombi", "Rongmei", "Ngangbam"],
        "sur": ["Singh", "Devi", "Sangma", "Marak", "Momin", "Lalhmingliana", "Konyak",
                "Jamir", "Ao", "Chakma", "Debbarma", "Rabha", "Basumatary", "Brahma"],
    },
}

REGION_WEIGHTS = {
    "hindi_belt": 0.24, "muslim": 0.14, "marathi": 0.09, "bengali": 0.08,
    "telugu": 0.07, "tamil": 0.07, "punjabi": 0.06, "rajasthani": 0.05,
    "gujarati": 0.05, "kannada": 0.05, "malayali": 0.04, "odia": 0.03,
    "christian": 0.02, "northeast": 0.01,
}

# Aliases / street names -- extremely common in Indian FIRs ("urf"/"@" = alias)
ALIAS_TOKENS = [
    "Bhai", "Anna", "Dada", "Pehalwan", "Chhota", "Bada", "Kaana", "Langda",
    "Tiger", "Lambu", "Tinku", "Pappu", "Guddu", "Chikna", "Kallu", "Doctor",
    "Master", "Ustad", "Seth", "Munna", "Raja", "Baba", "Sarkar", "Kaka",
    "Chacha", "Bandook", "Cheetah", "Kabootar", "Tempo", "Gullu", "Nanha",
]

# Transliteration variants used to seed *deliberate* duplicate records so that
# entity-resolution / "possible match" logic has something real to solve.
TRANSLITERATION_VARIANTS = {
    "Mohammed": ["Mohammad", "Muhammad", "Mohd.", "Md."],
    "Sheikh": ["Shaikh", "Shaik", "Shekh"],
    "Qureshi": ["Kureshi", "Quraishi"],
    "Siddiqui": ["Siddiqi", "Sidiqui"],
    "Chauhan": ["Chouhan", "Chowhan"],
    "Choudhary": ["Chaudhary", "Chowdhury", "Choudhury", "Chaudhari"],
    "Gowda": ["Gouda", "Gowdaa"],
    "Ghosh": ["Ghose", "Gosh"],
    "Deshmukh": ["Deshmuk", "Desmukh"],
    "Nair": ["Nayar", "Naiyar"],
    "Reddy": ["Reddi", "Reddey"],
    "Halder": ["Haldar", "Holder"],
    "Biswas": ["Bishwas", "Biswash"],
    "Rathore": ["Rathod", "Rathour"],
    "Bhattacharya": ["Bhattacharjee", "Bhattacharyya"],
}

# ---------------------------------------------------------------------------
# 2. GEOGRAPHY  (real states / cities with coordinates -> map-ready)
# ---------------------------------------------------------------------------

GEOGRAPHY = {
    "Maharashtra": [
        ("Mumbai", "Dongri", 18.9600, 72.8370), ("Mumbai", "Dharavi", 19.0400, 72.8500),
        ("Mumbai", "Kurla", 19.0700, 72.8790), ("Mumbai", "Bhendi Bazaar", 18.9580, 72.8300),
        ("Mumbai", "Andheri", 19.1197, 72.8468), ("Mumbai", "Malad", 19.1860, 72.8480),
        ("Thane", "Mumbra", 19.1890, 73.0230), ("Navi Mumbai", "Vashi", 19.0770, 72.9980),
        ("Pune", "Yerwada", 18.5510, 73.8880), ("Pune", "Kondhwa", 18.4650, 73.8900),
        ("Nagpur", "Kamptee", 21.2200, 79.1950), ("Nashik", "Panchavati", 20.0100, 73.7900),
        ("Aurangabad", "Cidco", 19.8760, 75.3430), ("Solapur", "Barshi", 18.2340, 75.6900),
    ],
    "Delhi": [
        ("New Delhi", "Chandni Chowk", 28.6560, 77.2300), ("New Delhi", "Seelampur", 28.6700, 77.2680),
        ("New Delhi", "Jamia Nagar", 28.5620, 77.2800), ("New Delhi", "Karol Bagh", 28.6510, 77.1900),
        ("New Delhi", "Najafgarh", 28.6090, 77.0100), ("New Delhi", "Nangloi", 28.6820, 77.0670),
        ("New Delhi", "Sangam Vihar", 28.4950, 77.2340), ("New Delhi", "Paharganj", 28.6440, 77.2140),
    ],
    "Uttar Pradesh": [
        ("Lucknow", "Aminabad", 26.8500, 80.9200), ("Kanpur", "Chakeri", 26.4200, 80.4100),
        ("Meerut", "Lisari Gate", 28.9800, 77.7060), ("Ghaziabad", "Loni", 28.7500, 77.2830),
        ("Noida", "Sector 63", 28.6270, 77.3800), ("Varanasi", "Chetganj", 25.3200, 82.9800),
        ("Gorakhpur", "Rajghat", 26.7600, 83.3700), ("Prayagraj", "Dhoomanganj", 25.4300, 81.8100),
        ("Muzaffarnagar", "Kutba", 29.4720, 77.7040), ("Bareilly", "Baradari", 28.3700, 79.4300),
        ("Azamgarh", "Sarai Mir", 26.0100, 82.8000), ("Jaunpur", "Line Bazaar", 25.7500, 82.6800),
    ],
    "Bihar": [
        ("Patna", "Kadamkuan", 25.6200, 85.1500), ("Munger", "Kasim Bazaar", 25.3700, 86.4700),
        ("Muzaffarpur", "Mithanpura", 26.1200, 85.3900), ("Gaya", "Chandauti", 24.7800, 85.0000),
        ("Siwan", "Mahadeva", 26.2200, 84.3600), ("Begusarai", "Barauni", 25.4200, 86.1300),
        ("Purnia", "Khajanchi Hat", 25.7800, 87.4700),
    ],
    "Jharkhand": [
        ("Jamtara", "Karmatanr", 23.9600, 86.8000), ("Deoghar", "Sarwan", 24.4800, 86.7000),
        ("Dhanbad", "Jharia", 23.7400, 86.4100), ("Ranchi", "Hatia", 23.3100, 85.3200),
        ("Giridih", "Bengabad", 24.1900, 86.3000),
    ],
    "West Bengal": [
        ("Kolkata", "Metiabruz", 22.5240, 88.3050), ("Kolkata", "Rajabazar", 22.5820, 88.3720),
        ("Malda", "Kaliachak", 24.9700, 88.0100), ("Murshidabad", "Jalangi", 24.1200, 88.4000),
        ("North 24 Parganas", "Bongaon", 23.0700, 88.8200), ("Siliguri", "Matigara", 26.7200, 88.3800),
        ("Nadia", "Karimpur", 23.9700, 88.6200),
    ],
    "Punjab": [
        ("Amritsar", "Ajnala", 31.8400, 74.7600), ("Tarn Taran", "Khalra", 31.4500, 74.5700),
        ("Ludhiana", "Jamalpur", 30.9200, 75.8500), ("Ferozepur", "Mamdot", 30.9200, 74.6100),
        ("Jalandhar", "Nakodar", 31.1200, 75.4800), ("Bathinda", "Rampura Phul", 30.2700, 75.2400),
    ],
    "Haryana": [
        ("Nuh", "Punhana", 27.8600, 77.2100), ("Gurugram", "Sohna", 28.2470, 77.0650),
        ("Sonipat", "Gohana", 29.1370, 76.7000), ("Hisar", "Barwala", 29.3700, 75.9100),
        ("Faridabad", "Ballabgarh", 28.3400, 77.3200),
    ],
    "Rajasthan": [
        ("Jodhpur", "Osian", 26.7200, 72.9100), ("Bikaner", "Nokha", 27.5600, 73.4700),
        ("Jaipur", "Chomu", 27.1700, 75.7200), ("Bharatpur", "Kaman", 27.6600, 77.2700),
        ("Alwar", "Ramgarh", 27.5200, 76.6200), ("Barmer", "Chohtan", 25.4900, 71.0400),
    ],
    "Gujarat": [
        ("Ahmedabad", "Juhapura", 23.0000, 72.5300), ("Surat", "Varachha", 21.2050, 72.8700),
        ("Kutch", "Mundra", 22.8390, 69.7210), ("Porbandar", "Kutiyana", 21.6200, 69.9800),
        ("Rajkot", "Gondal", 21.9600, 70.8000), ("Vadodara", "Karelibaug", 22.3200, 73.2000),
    ],
    "Madhya Pradesh": [
        ("Bhopal", "Bairagarh", 23.2800, 77.3300), ("Indore", "Rau", 22.6500, 75.8000),
        ("Khargone", "Sanawad", 22.1800, 75.9000), ("Gwalior", "Morar", 26.2300, 78.2100),
        ("Bhind", "Mehgaon", 26.5000, 78.6300), ("Jabalpur", "Gorakhpur", 23.1600, 79.9500),
    ],
    "Telangana": [
        ("Hyderabad", "Charminar", 17.3610, 78.4740), ("Hyderabad", "Kukatpally", 17.4840, 78.4000),
        ("Hyderabad", "Chandrayangutta", 17.3300, 78.4900), ("Warangal", "Hanamkonda", 18.0000, 79.5600),
        ("Nizamabad", "Bodhan", 18.6600, 77.8900),
    ],
    "Andhra Pradesh": [
        ("Visakhapatnam", "Gajuwaka", 17.6800, 83.2000), ("Vijayawada", "Gunadala", 16.5200, 80.6500),
        ("Guntur", "Mangalagiri", 16.4300, 80.5600), ("Kurnool", "Nandyal", 15.4800, 78.4800),
        ("Alluri Sitharama Raju", "Chintapalli", 17.8700, 82.3500),
    ],
    "Tamil Nadu": [
        ("Chennai", "Vyasarpadi", 13.1200, 80.2500), ("Chennai", "Kodungaiyur", 13.1300, 80.2400),
        ("Madurai", "Melur", 10.0300, 78.3400), ("Coimbatore", "Ukkadam", 10.9900, 76.9600),
        ("Tirunelveli", "Palayamkottai", 8.7200, 77.7400), ("Trichy", "Srirangam", 10.8600, 78.6900),
    ],
    "Karnataka": [
        ("Bengaluru", "KG Halli", 13.0000, 77.6100), ("Bengaluru", "Yeshwanthpur", 13.0230, 77.5500),
        ("Mangaluru", "Ullal", 12.8000, 74.8600), ("Kalaburagi", "Afzalpur", 17.2000, 76.3600),
        ("Ballari", "Sandur", 15.1000, 76.5500),
    ],
    "Kerala": [
        ("Kochi", "Mattancherry", 9.9580, 76.2590), ("Malappuram", "Tirur", 10.9200, 75.9200),
        ("Kozhikode", "Nadakkavu", 11.2700, 75.7800), ("Thrissur", "Chavakkad", 10.5900, 76.0100),
        ("Kannur", "Thalassery", 11.7500, 75.4900),
    ],
    "Odisha": [
        ("Bhubaneswar", "Nayapalli", 20.2900, 85.8100), ("Cuttack", "Jagatpur", 20.5200, 85.8600),
        ("Malkangiri", "Chitrakonda", 18.1000, 82.1000), ("Ganjam", "Berhampur", 19.3100, 84.7900),
    ],
    "Assam": [
        ("Guwahati", "Paltan Bazaar", 26.1800, 91.7500), ("Dhubri", "Golakganj", 26.0200, 89.8200),
        ("Karimganj", "Sutarkandi", 24.8700, 92.3500),
    ],
    "Manipur": [("Imphal", "Moreh", 24.2500, 94.3100), ("Churachandpur", "Tuibong", 24.3300, 93.6800)],
    "Goa": [("North Goa", "Anjuna", 15.5700, 73.7400), ("South Goa", "Vasco", 15.4000, 73.8100)],
    "Jammu and Kashmir": [("Srinagar", "Maisuma", 34.0700, 74.8000), ("Baramulla", "Uri", 34.0800, 74.0500)],
    "Chhattisgarh": [("Raipur", "Birgaon", 21.2800, 81.6300), ("Bijapur", "Bhairamgarh", 18.8000, 80.8000)],
    "Uttarakhand": [("Dehradun", "Clement Town", 30.2700, 78.0000), ("Haridwar", "Jwalapur", 29.9200, 78.1200)],
}

# Trans-national nodes used for hawala / narcotics / FICN corridors.
FOREIGN_HUBS = [
    ("UAE", "Dubai", 25.2048, 55.2708), ("UAE", "Sharjah", 25.3463, 55.4209),
    ("Nepal", "Kathmandu", 27.7172, 85.3240), ("Nepal", "Birgunj", 27.0100, 84.8800),
    ("Bangladesh", "Dhaka", 23.8103, 90.4125), ("Bangladesh", "Benapole", 23.0400, 88.9200),
    ("Pakistan", "Karachi", 24.8607, 67.0011), ("Myanmar", "Tamu", 24.2100, 94.3000),
    ("Thailand", "Bangkok", 13.7563, 100.5018), ("Malaysia", "Kuala Lumpur", 3.1390, 101.6869),
    ("Sri Lanka", "Colombo", 6.9271, 79.8612), ("Afghanistan", "Kandahar", 31.6100, 65.7100),
]

PLACE_TYPES = ["Residence", "Hideout", "Godown", "Hotel", "Dhaba", "Transit Point",
               "Border Crossing", "Cyber Cafe", "Jewellery Shop", "Scrap Yard",
               "Petrol Pump", "Farmhouse", "Warehouse", "Bar", "Gym", "Marriage Hall"]

# ---------------------------------------------------------------------------
# 3. STATUTE / CRIME TAXONOMY  (IPC + BNS 2023 + special acts -- all real)
# ---------------------------------------------------------------------------

CRIME_TYPES = {
    "MURDER":              {"ipc": "302",      "bns": "103(1)",  "severity": 10, "bailable": False},
    "ATTEMPT_TO_MURDER":   {"ipc": "307",      "bns": "109",     "severity": 8,  "bailable": False},
    "EXTORTION":           {"ipc": "384/387",  "bns": "308",     "severity": 6,  "bailable": False},
    "KIDNAP_FOR_RANSOM":   {"ipc": "364A",     "bns": "140(2)",  "severity": 9,  "bailable": False},
    "ROBBERY":             {"ipc": "392",      "bns": "309(4)",  "severity": 6,  "bailable": False},
    "DACOITY":             {"ipc": "395",      "bns": "310(2)",  "severity": 8,  "bailable": False},
    "CRIMINAL_CONSPIRACY": {"ipc": "120B",     "bns": "61(2)",   "severity": 5,  "bailable": False},
    "CHEATING_FRAUD":      {"ipc": "420",      "bns": "318(4)",  "severity": 5,  "bailable": True},
    "FORGERY":             {"ipc": "465/468",  "bns": "336(3)",  "severity": 4,  "bailable": True},
    "NDPS_TRAFFICKING":    {"ipc": "NDPS 21(c)/29", "bns": "-",  "severity": 9,  "bailable": False},
    "NDPS_POSSESSION":     {"ipc": "NDPS 22(b)",    "bns": "-",  "severity": 5,  "bailable": False},
    "ARMS_ACT":            {"ipc": "Arms Act 25/27", "bns": "-", "severity": 6,  "bailable": False},
    "MONEY_LAUNDERING":    {"ipc": "PMLA 3/4",  "bns": "-",      "severity": 7,  "bailable": False},
    "CYBER_FRAUD":         {"ipc": "IT Act 66C/66D", "bns": "319(2)", "severity": 5, "bailable": True},
    "HUMAN_TRAFFICKING":   {"ipc": "370/372",  "bns": "143",     "severity": 9,  "bailable": False},
    "FICN_COUNTERFEIT":    {"ipc": "489B/489C", "bns": "179",    "severity": 8,  "bailable": False},
    "ILLEGAL_MINING":      {"ipc": "MMDR 21(1)", "bns": "-",     "severity": 4,  "bailable": True},
    "SMUGGLING_CUSTOMS":   {"ipc": "Customs Act 135", "bns": "-", "severity": 5, "bailable": True},
    "VEHICLE_THEFT":       {"ipc": "379/411",  "bns": "303(2)",  "severity": 3,  "bailable": True},
    "BETTING_GAMBLING":    {"ipc": "Gambling Act 3/4", "bns": "-", "severity": 2, "bailable": True},
    "ORGANISED_CRIME":     {"ipc": "MCOCA 3(1)", "bns": "111",   "severity": 10, "bailable": False},
    "RIOTING":             {"ipc": "147/148",  "bns": "191(2)",  "severity": 4,  "bailable": True},
    "LAND_GRABBING":       {"ipc": "441/447",  "bns": "329",     "severity": 4,  "bailable": True},
    "CHIT_FUND_PONZI":     {"ipc": "BUDS Act 21", "bns": "318(4)", "severity": 6, "bailable": True},
    "WILDLIFE_TRAFFICKING":{"ipc": "WLPA 51",  "bns": "-",       "severity": 6,  "bailable": False},
    "LIQUOR_SMUGGLING":    {"ipc": "Excise Act 47", "bns": "-",  "severity": 3,  "bailable": True},
}

# ---------------------------------------------------------------------------
# 4. SYNDICATE ARCHETYPES
#    Modelled on *publicly documented typologies* of Indian organised crime.
#    No archetype represents any specific real gang or person.
# ---------------------------------------------------------------------------

SYNDICATE_ARCHETYPES = [
    {
        "code": "SYN-EXT", "label": "Urban Extortion & Land Syndicate",
        "base_states": ["Maharashtra", "Gujarat"], "reach": ["Delhi", "Karnataka"],
        "crimes": ["EXTORTION", "LAND_GRABBING", "ATTEMPT_TO_MURDER", "MURDER",
                   "ORGANISED_CRIME", "CRIMINAL_CONSPIRACY"],
        "foreign": ["UAE"], "size": (95, 130), "name_regions": ["marathi", "muslim", "gujarati"],
        "front_types": ["Builders", "Developers", "Realty", "Infra", "Enterprises"],
    },
    {
        "code": "SYN-HER", "label": "Golden Crescent Heroin Corridor",
        "base_states": ["Punjab", "Rajasthan"], "reach": ["Delhi", "Haryana", "Jammu and Kashmir"],
        "crimes": ["NDPS_TRAFFICKING", "NDPS_POSSESSION", "ARMS_ACT", "MONEY_LAUNDERING",
                   "CRIMINAL_CONSPIRACY"],
        "foreign": ["Pakistan", "Afghanistan", "UAE"], "size": (85, 115),
        "name_regions": ["punjabi", "rajasthani", "muslim"],
        "front_types": ["Agro Traders", "Transport Co", "Cold Storage", "Rice Mills"],
    },
    {
        "code": "SYN-CYB", "label": "Vishing / Digital-Arrest Cyber Fraud Network",
        "base_states": ["Jharkhand", "Bihar", "Haryana", "West Bengal"],
        "reach": ["Delhi", "Uttar Pradesh", "Karnataka"],
        "crimes": ["CYBER_FRAUD", "CHEATING_FRAUD", "FORGERY", "MONEY_LAUNDERING"],
        "foreign": ["Nepal", "Bangladesh", "Myanmar", "Thailand"], "size": (120, 160),
        "name_regions": ["hindi_belt", "muslim", "bengali"],
        "front_types": ["Digital Services", "Technologies", "Marketing Solutions", "BPO Services"],
    },
    {
        "code": "SYN-HAW", "label": "Hawala & Trade-Based Laundering Ring",
        "base_states": ["Delhi", "Kerala", "Maharashtra", "Gujarat"],
        "reach": ["Tamil Nadu", "Telangana", "West Bengal"],
        "crimes": ["MONEY_LAUNDERING", "SMUGGLING_CUSTOMS", "FORGERY", "CHEATING_FRAUD"],
        "foreign": ["UAE", "Malaysia", "Sri Lanka"], "size": (70, 95),
        "name_regions": ["muslim", "malayali", "gujarati", "hindi_belt"],
        "front_types": ["Exim", "Trading Co", "Gems & Jewels", "Forex Services", "Logistics"],
    },
    {
        "code": "SYN-MIN", "label": "Illegal Sand & Mineral Mining Mafia",
        "base_states": ["Uttar Pradesh", "Madhya Pradesh", "Tamil Nadu", "Karnataka"],
        "reach": ["Rajasthan", "Bihar"],
        "crimes": ["ILLEGAL_MINING", "EXTORTION", "ATTEMPT_TO_MURDER", "RIOTING", "MURDER"],
        "foreign": [], "size": (60, 85), "name_regions": ["hindi_belt", "tamil", "kannada"],
        "front_types": ["Minerals", "Stone Crushers", "Earth Movers", "Constructions"],
    },
    {
        "code": "SYN-TRF", "label": "Cross-Border Human Trafficking Network",
        "base_states": ["West Bengal", "Assam", "Bihar"],
        "reach": ["Delhi", "Maharashtra", "Karnataka", "Haryana"],
        "crimes": ["HUMAN_TRAFFICKING", "FORGERY", "CRIMINAL_CONSPIRACY", "CHEATING_FRAUD"],
        "foreign": ["Bangladesh", "Nepal"], "size": (55, 80),
        "name_regions": ["bengali", "muslim", "hindi_belt"],
        "front_types": ["Placement Agency", "Manpower Services", "Travels", "Consultancy"],
    },
    {
        "code": "SYN-ARM", "label": "Illicit Arms Manufacture & Supply Chain",
        "base_states": ["Bihar", "Madhya Pradesh", "Uttar Pradesh"],
        "reach": ["Jharkhand", "West Bengal", "Maharashtra"],
        "crimes": ["ARMS_ACT", "CRIMINAL_CONSPIRACY", "MURDER", "ORGANISED_CRIME"],
        "foreign": ["Nepal"], "size": (45, 70), "name_regions": ["hindi_belt", "muslim"],
        "front_types": ["Hardware Works", "Engineering Works", "Auto Parts", "Fabricators"],
    },
    {
        "code": "SYN-VEH", "label": "Inter-State Vehicle Theft & Chop-Shop Ring",
        "base_states": ["Delhi", "Haryana", "Uttar Pradesh"],
        "reach": ["Punjab", "Rajasthan", "Bihar"],
        "crimes": ["VEHICLE_THEFT", "FORGERY", "CHEATING_FRAUD", "ROBBERY"],
        "foreign": ["Nepal"], "size": (50, 75), "name_regions": ["hindi_belt", "muslim", "punjabi"],
        "front_types": ["Motors", "Auto Deals", "Car Bazaar", "Spare Parts"],
    },
    {
        "code": "SYN-FIC", "label": "Fake Indian Currency Note Circulation Ring",
        "base_states": ["West Bengal", "Bihar"], "reach": ["Uttar Pradesh", "Delhi", "Assam"],
        "crimes": ["FICN_COUNTERFEIT", "SMUGGLING_CUSTOMS", "CRIMINAL_CONSPIRACY"],
        "foreign": ["Bangladesh", "Nepal", "Pakistan"], "size": (40, 60),
        "name_regions": ["bengali", "muslim", "hindi_belt"],
        "front_types": ["Printers", "Paper Traders", "Stationers", "Packaging"],
    },
    {
        "code": "SYN-GAN", "label": "Eastern Ghats Ganja Supply Corridor",
        "base_states": ["Odisha", "Andhra Pradesh", "Chhattisgarh"],
        "reach": ["Tamil Nadu", "Karnataka", "Telangana", "Maharashtra"],
        "crimes": ["NDPS_TRAFFICKING", "NDPS_POSSESSION", "CRIMINAL_CONSPIRACY", "ARMS_ACT"],
        "foreign": [], "size": (55, 80), "name_regions": ["odia", "telugu", "tamil"],
        "front_types": ["Roadways", "Transport", "Agro Products", "Timber Traders"],
    },
    {
        "code": "SYN-PON", "label": "Multi-State Chit Fund / Ponzi Operation",
        "base_states": ["West Bengal", "Odisha", "Assam"], "reach": ["Bihar", "Jharkhand"],
        "crimes": ["CHIT_FUND_PONZI", "CHEATING_FRAUD", "MONEY_LAUNDERING", "FORGERY"],
        "foreign": ["UAE"], "size": (45, 70), "name_regions": ["bengali", "odia", "hindi_belt"],
        "front_types": ["Agro Farms", "Realty Infra", "Multi Trade", "Nidhi Ltd", "Plantations"],
    },
    {
        "code": "SYN-BET", "label": "Cricket Betting & Match-Fixing Syndicate",
        "base_states": ["Gujarat", "Maharashtra", "Delhi", "Rajasthan"],
        "reach": ["Karnataka", "Telangana"],
        "crimes": ["BETTING_GAMBLING", "MONEY_LAUNDERING", "CHEATING_FRAUD", "EXTORTION"],
        "foreign": ["UAE", "Sri Lanka", "Malaysia"], "size": (50, 75),
        "name_regions": ["gujarati", "marathi", "hindi_belt", "muslim"],
        "front_types": ["Sports Ventures", "Event Management", "Hospitality", "Media Works"],
    },
    {
        "code": "SYN-KDN", "label": "Kidnapping-for-Ransom Crew",
        "base_states": ["Bihar", "Jharkhand", "Uttar Pradesh"], "reach": ["Delhi", "West Bengal"],
        "crimes": ["KIDNAP_FOR_RANSOM", "MURDER", "ARMS_ACT", "EXTORTION", "ORGANISED_CRIME"],
        "foreign": ["Nepal"], "size": (35, 55), "name_regions": ["hindi_belt", "muslim"],
        "front_types": ["Contractors", "Suppliers", "Traders"],
    },
    {
        "code": "SYN-SHK", "label": "Contract Shooter / Supari Network",
        "base_states": ["Haryana", "Uttar Pradesh", "Rajasthan", "Punjab"],
        "reach": ["Delhi", "Maharashtra", "Madhya Pradesh"],
        "crimes": ["MURDER", "ATTEMPT_TO_MURDER", "ARMS_ACT", "EXTORTION", "ORGANISED_CRIME"],
        "foreign": ["UAE", "Nepal"], "size": (45, 65),
        "name_regions": ["hindi_belt", "punjabi", "rajasthani"],
        "front_types": ["Gym & Fitness", "Property Dealers", "Security Services"],
    },
    {
        "code": "SYN-WLD", "label": "Wildlife & Red-Sanders Trafficking Ring",
        "base_states": ["Andhra Pradesh", "Tamil Nadu", "Madhya Pradesh", "Assam"],
        "reach": ["Delhi", "West Bengal", "Manipur"],
        "crimes": ["WILDLIFE_TRAFFICKING", "SMUGGLING_CUSTOMS", "FORGERY", "CRIMINAL_CONSPIRACY"],
        "foreign": ["Nepal", "Myanmar", "Thailand"], "size": (30, 50),
        "name_regions": ["telugu", "tamil", "northeast", "hindi_belt"],
        "front_types": ["Forest Produce", "Handicrafts", "Exports", "Timber Co"],
    },
]

# ---------------------------------------------------------------------------
# 5. ROLES  (drives graph topology: who is central, who is a broker)
# ---------------------------------------------------------------------------

ROLES = {
    "KINGPIN":         {"share": 0.012, "risk": (88, 99), "degree": "low",    "influence": 1.00},
    "LIEUTENANT":      {"share": 0.048, "risk": (72, 92), "degree": "high",   "influence": 0.80},
    "FINANCIER":       {"share": 0.040, "risk": (65, 90), "degree": "medium", "influence": 0.75},
    "HAWALA_OPERATOR": {"share": 0.038, "risk": (60, 88), "degree": "medium", "influence": 0.72},
    "LOGISTICS":       {"share": 0.075, "risk": (45, 70), "degree": "medium", "influence": 0.45},
    "RECRUITER":       {"share": 0.055, "risk": (48, 72), "degree": "high",   "influence": 0.50},
    "FIELD_OPERATIVE": {"share": 0.230, "risk": (35, 68), "degree": "medium", "influence": 0.25},
    "SHOOTER":         {"share": 0.060, "risk": (70, 90), "degree": "low",    "influence": 0.35},
    "MULE":            {"share": 0.185, "risk": (15, 40), "degree": "low",    "influence": 0.08},
    "FIXER":           {"share": 0.045, "risk": (55, 80), "degree": "medium", "influence": 0.60},
    "FENCE":           {"share": 0.045, "risk": (40, 65), "degree": "medium", "influence": 0.30},
    "INFORMANT":       {"share": 0.030, "risk": (20, 45), "degree": "medium", "influence": 0.20},
    "CORRUPT_OFFICIAL":{"share": 0.022, "risk": (50, 78), "degree": "low",    "influence": 0.65},
    "TECH_HANDLER":    {"share": 0.040, "risk": (45, 75), "degree": "medium", "influence": 0.40},
    "COURIER":         {"share": 0.075, "risk": (30, 55), "degree": "medium", "influence": 0.18},
}

CUSTODY_STATUS = ["AT_LARGE", "IN_JUDICIAL_CUSTODY", "ON_BAIL", "ABSCONDING",
                  "DECLARED_PO", "UNDER_SURVEILLANCE", "DECEASED", "EXTRADITION_PENDING"]

# ---------------------------------------------------------------------------
# 6. TELECOM / FINANCE / VEHICLE REFERENCE
# ---------------------------------------------------------------------------

TELECOM_OPERATORS = ["Jio", "Airtel", "Vi", "BSNL", "MTNL"]
MOBILE_PREFIXES = ["70", "71", "72", "73", "74", "75", "76", "77", "78", "79",
                   "80", "81", "82", "83", "84", "85", "86", "87", "88", "89",
                   "90", "91", "92", "93", "94", "95", "96", "97", "98", "99"]

BANKS = ["State Bank of India", "Punjab National Bank", "Bank of Baroda", "HDFC Bank",
         "ICICI Bank", "Axis Bank", "Canara Bank", "Union Bank of India", "Kotak Mahindra Bank",
         "IndusInd Bank", "Yes Bank", "IDFC First Bank", "Bandhan Bank", "Federal Bank",
         "Karur Vysya Bank", "Bank of India", "Central Bank of India", "Indian Overseas Bank",
         "AU Small Finance Bank", "Airtel Payments Bank", "Paytm Payments Bank"]

TXN_CHANNELS = ["UPI", "IMPS", "NEFT", "RTGS", "CASH_DEPOSIT", "CASH_WITHDRAWAL",
                "CHEQUE", "DEMAND_DRAFT", "WALLET_TRANSFER", "CRYPTO_P2P",
                "ANGADIA", "HAWALA_TOKEN"]

VEHICLE_MAKES = [
    ("Maruti Suzuki", ["Swift", "Dzire", "Baleno", "Ertiga", "Alto", "Eeco", "Brezza"]),
    ("Hyundai", ["i20", "Creta", "Verna", "Venue", "Santro"]),
    ("Mahindra", ["Scorpio", "Bolero", "XUV700", "Thar", "Pick-Up"]),
    ("Tata", ["Nexon", "Harrier", "Sumo", "407", "Ace", "Safari"]),
    ("Toyota", ["Innova Crysta", "Fortuner", "Etios"]),
    ("Honda", ["City", "Amaze"]),
    ("Royal Enfield", ["Classic 350", "Bullet 350", "Himalayan"]),
    ("Bajaj", ["Pulsar 150", "Pulsar 220", "Platina"]),
    ("Hero", ["Splendor Plus", "HF Deluxe", "Passion Pro"]),
    ("Ashok Leyland", ["Dost", "Ecomet", "Boss"]),
    ("Eicher", ["Pro 2049", "Pro 3015"]),
]

RTO_CODES = {
    "Maharashtra": ["MH01", "MH02", "MH03", "MH04", "MH12", "MH14", "MH20", "MH31", "MH43", "MH47"],
    "Delhi": ["DL01", "DL02", "DL03", "DL04", "DL07", "DL08", "DL09", "DL10", "DL13"],
    "Uttar Pradesh": ["UP32", "UP16", "UP15", "UP14", "UP65", "UP78", "UP80", "UP50", "UP62"],
    "Bihar": ["BR01", "BR06", "BR09", "BR11", "BR28", "BR33"],
    "Jharkhand": ["JH01", "JH10", "JH13", "JH20"],
    "West Bengal": ["WB02", "WB06", "WB20", "WB24", "WB57", "WB73"],
    "Punjab": ["PB02", "PB08", "PB10", "PB11", "PB46", "PB65"],
    "Haryana": ["HR26", "HR51", "HR10", "HR20", "HR38", "HR55"],
    "Rajasthan": ["RJ14", "RJ19", "RJ02", "RJ05", "RJ07", "RJ27"],
    "Gujarat": ["GJ01", "GJ05", "GJ06", "GJ18", "GJ27", "GJ12"],
    "Madhya Pradesh": ["MP04", "MP09", "MP07", "MP20", "MP13", "MP30"],
    "Telangana": ["TS07", "TS09", "TS08", "TS10", "TS16"],
    "Andhra Pradesh": ["AP31", "AP16", "AP07", "AP21", "AP39"],
    "Tamil Nadu": ["TN01", "TN09", "TN10", "TN37", "TN45", "TN67"],
    "Karnataka": ["KA01", "KA03", "KA05", "KA19", "KA32", "KA41"],
    "Kerala": ["KL07", "KL01", "KL11", "KL10", "KL13"],
    "Odisha": ["OD02", "OD05", "OD33", "OD07"],
    "Assam": ["AS01", "AS15", "AS10"],
    "Manipur": ["MN01", "MN02"],
    "Goa": ["GA01", "GA03"],
    "Jammu and Kashmir": ["JK01", "JK02", "JK05"],
    "Chhattisgarh": ["CG04", "CG07", "CG10"],
    "Uttarakhand": ["UK07", "UK08", "UK16"],
}

WEAPON_TYPES = ["Country-made pistol (katta)", ".32 bore revolver", "9mm pistol",
                "SBBL gun", "DBBL gun", "AK-series rifle", "Machete (chopper)",
                "Sword", "Improvised explosive material", "Air weapon", "Knife"]

CONTRABAND = {
    "NDPS_TRAFFICKING": ["Heroin", "Brown sugar", "Methamphetamine", "Ganja", "Charas",
                         "Opium", "Cocaine", "Mephedrone (MD)", "Alprazolam tablets",
                         "Pseudoephedrine", "Tramadol capsules"],
    "NDPS_POSSESSION": ["Heroin", "Ganja", "Charas", "Alprazolam tablets", "Brown sugar"],
    "ARMS_ACT": ["Country-made pistols", "Live cartridges", "Rifle barrels", "Semi-finished frames"],
    "FICN_COUNTERFEIT": ["FICN Rs.500 notes", "FICN Rs.2000 notes", "Security ink", "Intaglio plates"],
    "WILDLIFE_TRAFFICKING": ["Red sanders logs", "Pangolin scales", "Tiger nails", "Star tortoises",
                             "Elephant ivory", "Shahtoosh shawls"],
    "SMUGGLING_CUSTOMS": ["Gold biscuits", "Foreign cigarettes", "Betel nut (supari)",
                          "Mobile phones", "Chinese firecrackers"],
    "LIQUOR_SMUGGLING": ["IMFL cases", "Country liquor pouches", "Spirit barrels"],
}

# ---------------------------------------------------------------------------
# 7. AGENCIES / SOURCES
# ---------------------------------------------------------------------------

AGENCIES = ["State Police - Crime Branch", "Anti-Narcotics Cell", "Economic Offences Wing",
            "Special Task Force (STF)", "Anti-Terrorism Squad (ATS)", "Cyber Crime Cell",
            "Narcotics Control Bureau", "Directorate of Revenue Intelligence",
            "Enforcement Directorate", "Central Bureau of Investigation",
            "Railway Protection Force", "State Intelligence Department",
            "Border Security Force - Intel", "Income Tax Investigation Wing"]

SOURCE_TYPES = ["FIR", "CDR", "BANK_STATEMENT", "SURVEILLANCE_REPORT", "SOCIAL_MEDIA_INTEL",
                "CRIMINAL_HISTORY_DB", "INTELLIGENCE_REPORT", "IPDR", "TOWER_DUMP",
                "INFORMANT_TIP", "SEIZURE_MEMO", "CHARGESHEET", "PASSPORT_IMMIGRATION"]

RELIABILITY_GRADES = ["A", "B", "C", "D", "E", "F"]   # NATO Admiralty source reliability
CREDIBILITY_GRADES = ["1", "2", "3", "4", "5", "6"]   # NATO Admiralty info credibility

# ---------------------------------------------------------------------------
# 8. RELATIONSHIP TAXONOMY  (edge types for the graph)
# ---------------------------------------------------------------------------

PERSON_PERSON_RELATIONS = [
    ("ASSOCIATE_OF", 0.30, True),        # (label, weight, symmetric)
    ("CO_ACCUSED_WITH", 0.16, True),
    ("REPORTS_TO", 0.13, False),
    ("FAMILY_OF", 0.09, True),
    ("FINANCES", 0.07, False),
    ("RECRUITED_BY", 0.06, False),
    ("SHARES_HIDEOUT_WITH", 0.05, True),
    ("RIVAL_OF", 0.04, True),
    ("CELLMATE_OF", 0.04, True),
    ("HANDLER_OF", 0.03, False),
    ("SUPPLIES_TO", 0.03, False),
]

FAMILY_SUBTYPES = ["Brother", "Father", "Son", "Cousin", "Brother-in-law",
                   "Nephew", "Uncle", "Spouse", "Maternal cousin"]

# ---------------------------------------------------------------------------
# 9. NARRATIVE TEMPLATES  (unstructured text for the NLP / NER pipeline)
# ---------------------------------------------------------------------------

FIR_OPENINGS = [
    "On {date} at about {time} hrs, a written complaint was received at {ps} Police Station from {complainant}, resident of {area}, {city}.",
    "This FIR is registered on the basis of a source report placed before the SHO, {ps} Police Station, {city} on {date} at {time} hrs.",
    "On receipt of secret information on {date} at {time} hrs, a raiding party was constituted at {ps} Police Station, {city} under the supervision of the undersigned.",
    "A complaint dated {date} was forwarded by the {agency} to {ps} Police Station, {city}, disclosing commission of a cognizable offence.",
    "During patrolling duty on {date} at {time} hrs near {area}, {city}, the patrolling staff of {ps} Police Station noticed suspicious movement.",
]

FIR_BODY_TEMPLATES = {
    "NDPS_TRAFFICKING": [
        "The team intercepted {a_vehicle} bearing registration {plate} near {area}. On search, {qty} of {contraband} was recovered from a cavity concealed in the {cavity}. The occupant disclosed his identity as {p1}, r/o {area2}, {city2}. During sustained interrogation he revealed that the consignment was arranged by one {p2} @ {alias2} and was to be delivered to {p3} at {area3}. Mobile handset bearing number {phone1} was seized from the accused; call records indicate frequent contact with {phone2}.",
        "Acting on the information, the party laid a naka near {area}. At about {time} hrs, {p1} @ {alias1} was apprehended while carrying {qty} of {contraband} in a black polythene bag. He stated that the material was handed over to him by {p2}, r/o {area2}, who works at the instance of {p3}. The seized contraband was weighed in the presence of independent witnesses and sealed with seal impression '{seal}'.",
    ],
    "NDPS_POSSESSION": [
        "During checking near {area}, {city}, {p1} was found in possession of {qty} of {contraband}. On being questioned he named {p2} as the person who supplied the material. Mobile number {phone1} recovered from him shows repeated contact with {phone2}.",
    ],
    "CYBER_FRAUD": [
        "The complainant {complainant} stated that he received a video call from number {phone1} whose caller introduced himself as an officer of a central agency and asserted that a parcel in the complainant's name contained contraband. Under sustained threat the complainant transferred Rs.{amount} in {n} tranches to account no. {account1} maintained with {bank1}. Preliminary enquiry reveals the said account is operated by {p1}, r/o {area}, {city}, and funds were immediately layered to account {account2} of {bank2} held by {p2}.",
        "It is alleged that the accused persons operating from {area}, {city} created a fake customer-care listing and induced the complainant to install a screen-sharing application. An amount of Rs.{amount} was siphoned off through {n} UPI transactions to a VPA linked with account {account1}. Technical analysis of IP logs points to devices used by {p1} and {p2}, both allegedly working under the direction of {p3} @ {alias3}.",
    ],
    "EXTORTION": [
        "The complainant {complainant}, a {occupation} of {area}, {city}, stated that on {date} a threatening call was received from mobile number {phone1}. The caller identified himself as a member of the group of {p1} @ {alias1} and demanded Rs.{amount} as protection money, failing which the complainant was threatened with dire consequences. Two unidentified persons on a motorcycle bearing {plate} fired in the air outside the complainant's premises.",
        "It is stated that {p1} along with his associates {p2} and {p3} came to the office of the complainant at {area} and demanded Rs.{amount}. On refusal, they caused damage to property and brandished a firearm. CCTV footage of the premises has been seized. The mobile number {phone1} used to send subsequent threat messages is under technical verification.",
    ],
    "MONEY_LAUNDERING": [
        "Investigation reveals that {org1}, a concern operating from {area}, {city} with {p1} and {p2} as its directors, received Rs.{amount} in its account {account1} with {bank1} from {n} unrelated entities within a span of {days} days. The funds were withdrawn in cash almost immediately or transferred to {account2} held with {bank2}. Enquiry establishes that {p1} is a benami of {p3} @ {alias3}, presently believed to be operating from {foreign_city}.",
        "It has been recorded that layered transfers aggregating Rs.{amount} moved through {n} accounts controlled by {p1}. Angadia receipts and coded hawala tokens bearing the mark '{seal}' were recovered during search of the premises of {p2} at {area}, {city}.",
    ],
    "MURDER": [
        "On {date} at about {time} hrs, the deceased {victim}, aged {age} years, r/o {area}, {city}, was shot at by two unidentified assailants who arrived on a motorcycle bearing registration {plate}. The deceased was shifted to hospital where he was declared brought dead. Enquiry indicates prior enmity with {p1} @ {alias1}, who had been demanding Rs.{amount} from the deceased.",
        "The body of {victim} was recovered from {area}, {city}, with injuries caused by a sharp-edged weapon. Last-seen evidence and tower-dump analysis place mobile numbers {phone1} and {phone2}, used by {p1} and {p2} respectively, within the same cell site at the material time. Both are known associates of {p3}.",
    ],
    "ATTEMPT_TO_MURDER": [
        "The complainant states that on {date} at about {time} hrs, while he was returning to his residence at {area}, {city}, {p1} @ {alias1} along with {p2} fired at him from a country-made pistol. The complainant sustained injuries on the leg. The assailants fled on a motorcycle bearing {plate}. The motive is stated to be a dispute over payment of Rs.{amount}.",
    ],
    "ARMS_ACT": [
        "During a raid at a workshop situated at {area}, {city}, {n} semi-finished country-made pistols, {n2} live cartridges and machinery used for boring barrels were recovered. {p1} was apprehended from the spot while {p2} managed to escape. Interrogation reveals that finished weapons were supplied to {p3} at {city2} for onward delivery.",
    ],
    "HUMAN_TRAFFICKING": [
        "The complainant stated that the daughter of the complainant, aged {age} years, was taken from {area2}, {city2} on the pretext of employment by {p1} and {p2}. Enquiry reveals that the victim was transported via {city} and confined at a premises at {area}. The placement agency {org1} operated by {p3} is found to have issued forged identity documents.",
    ],
    "FICN_COUNTERFEIT": [
        "On personal search of {p1} @ {alias1}, FICN of face value Rs.{amount} in the denomination of Rs.500 was recovered from a concealed pouch. The accused disclosed that the consignment was received near the {area} border outpost from a carrier of {p2}, and was to be delivered to {p3} at {city2}.",
    ],
    "ILLEGAL_MINING": [
        "A joint team of the Mining Department and {ps} Police Station intercepted {n} tractor-trolleys and {n2} tippers illegally transporting sand from the {area} riverbed. The vehicles bearing registration {plate} and others were seized. The operation is stated to be carried out at the behest of {p1} @ {alias1}, who allegedly maintains armed muscle to prevent enforcement action.",
    ],
    "KIDNAP_FOR_RANSOM": [
        "It is alleged that on {date} at about {time} hrs, the son of the complainant, aged {age} years, was abducted from near {area}, {city} by four persons travelling in {a_vehicle} bearing {plate}. A ransom demand of Rs.{amount} was made from mobile number {phone1}. Technical surveillance indicates the said number was used in the vicinity of {area2}, a location frequented by {p1} and his associate {p2}.",
    ],
    "VEHICLE_THEFT": [
        "The complainant reported that his {vehicle} bearing registration {plate} was stolen from outside his residence at {area}, {city} on {date}. During investigation the vehicle was traced to a scrap yard at {area2} operated by {p1}, where the chassis number was found tampered. {p2} and {p3} are stated to have arranged forged registration papers.",
    ],
    "CHIT_FUND_PONZI": [
        "Numerous depositors of {area}, {city} have alleged that {org1}, promoted by {p1} and {p2}, collected deposits aggregating Rs.{amount} promising unrealistic returns, and thereafter closed its collection centres. Enquiry reveals that funds were diverted to account {account1} with {bank1} and further to {account2} with {bank2} held in the name of a concern controlled by {p3}.",
    ],
    "WILDLIFE_TRAFFICKING": [
        "A consignment declared as agricultural produce and moving in {a_vehicle} bearing {plate} was intercepted near {area}, {city}. On examination, {contraband} concealed beneath the declared cargo was recovered. The driver named {p1} as the consignor and {p2} as the intended recipient at {city2}. {p3} is stated to have arranged the forged transit documents.",
    ],
    "SMUGGLING_CUSTOMS": [
        "Acting on specific intelligence, {contraband} valued at Rs.{amount} was recovered from a consignment cleared in the name of {org1} at {area}, {city}. {p1}, the customs house agent, is stated to have facilitated clearance at the instance of {p2}. Payment is stated to have been settled through hawala channels operated by {p3}.",
    ],
    "FORGERY": [
        "The complainant {complainant} stated that a sale deed purporting to bear the complainant's signature was presented for registration at the Sub-Registrar's office at {area}, {city}. On verification the document was found to be fabricated. Enquiry reveals that {p1} @ {alias1} arranged the forged stamp paper through {p2}, and that {p3} impersonated the complainant before the registering authority. A sum of Rs.{amount} is involved.",
        "During search of the premises of {p1} at {area}, {city}, {n} rubber stamps of various offices, {n2} blank letterheads and a laptop containing scanned signatures were recovered. The accused disclosed that forged identity and transport documents were prepared at the instance of {p2} and delivered to {p3} at {city2}. Mobile number {phone1} recovered from the spot shows sustained contact with {phone2}.",
    ],
    "CRIMINAL_CONSPIRACY": [
        "Source information disclosed that {p1} @ {alias1}, {p2} and {p3} assembled at a {place_type} at {area}, {city} on {date} at about {time} hrs and hatched a conspiracy to commit a cognizable offence. On the strength of the information a raid was conducted; hand-written notes bearing the mark '{seal}', {n} mobile handsets and Rs.{amount} in cash were recovered from the spot.",
        "Investigation establishes a meeting of minds between {p1}, r/o {area}, {city} and {p2} of {area2}, {city2}. Call detail records of {phone1} and {phone2} show {n} contacts in the {days} days preceding the offence. Funds aggregating Rs.{amount} were moved to account {account1} of {bank1} in the same period.",
    ],
    "CHEATING_FRAUD": [
        "The complainant {complainant}, a {occupation} of {area}, {city}, stated that the accused {p1} @ {alias1} held out an assurance of allotment of a plot and induced the complainant to part with Rs.{amount}, paid in {n} instalments to account {account1} maintained with {bank1}. Neither allotment nor refund followed. Enquiry reveals that the account is operated by {p2} and that the concern {org1} shown in the agreement is not in existence at the stated address.",
        "It is alleged that {p1} and {p2}, holding themselves out as representatives of {org1}, collected Rs.{amount} from {n} persons of {area}, {city} against promised overseas employment. The offer letters and visa documents supplied were found to be fabricated. The premises were vacated and mobile number {phone1} switched off. {p3} is stated to have received the collections in cash.",
    ],
    "ORGANISED_CRIME": [
        "It is placed on record that {p1} @ {alias1} heads an organised crime syndicate operating in {city} and adjoining districts, and that {n} chargesheets have been filed against members of the syndicate in the preceding {days} months. The syndicate, through {p2} and {p3}, has been engaged in a continuing unlawful activity for pecuniary benefit. Proceeds aggregating Rs.{amount} have been traced to account {account1} of {bank1} and to {org1}.",
        "The competent authority having accorded prior approval, provisions relating to organised crime are invoked against {p1}, {p2} and {p3}. The gang operates from {area}, {city} under the direction of {p1} @ {alias1}, who is reported to be presently in {foreign_city}. Instructions are relayed over mobile number {phone1} to {phone2}, and extortion collections are routed through {org1}.",
    ],
    "DACOITY": [
        "The complainant stated that on {date} at about {time} hrs, while the goods vehicle bearing {plate} was proceeding through {area}, {city}, {n} armed persons intercepted it, overpowered the driver and decamped with the consignment valued at Rs.{amount}. Two of the assailants have been identified as {p1} @ {alias1} and {p2}. The gang is stated to be led by {p3}, who arranges disposal of the looted property.",
    ],
    "RIOTING": [
        "On {date} at about {time} hrs, an unlawful assembly of about {n} persons armed with lathis and sharp-edged weapons gathered at {area}, {city} and caused damage to property estimated at Rs.{amount}. {p1} @ {alias1}, {p2} and {p3} were identified from video footage as having instigated the assembly. Enquiry indicates the incident arose out of a pre-existing dispute over possession.",
    ],
    "ROBBERY": [
        "The complainant {complainant}, a {occupation}, stated that on {date} at about {time} hrs, two persons on a motorcycle bearing {plate} intercepted him near {area}, {city}, brandished a country-made pistol and robbed the complainant of cash and ornaments valued at Rs.{amount}. The assailants have been identified as {p1} @ {alias1} and {p2}. The stolen property is stated to have been disposed of through {p3}, a receiver operating at {area2}.",
    ],
    "LAND_GRABBING": [
        "{complainant}, the recorded owner of a plot situated at {area}, {city}, has stated as follows. On {date}, {p1} @ {alias1} along with {p2}, {p3} and about {n} others forcibly entered upon the plot, demolished the boundary wall and raised a temporary structure. A fabricated sale deed showing consideration of Rs.{amount} was subsequently produced. The complainant was threatened over mobile number {phone1} when he objected.",
    ],
    "BETTING_GAMBLING": [
        "On the basis of secret information a raid was conducted at a {place_type} at {area}, {city} on {date} at {time} hrs. {n} persons were found accepting bets on a live cricket match. {n2} mobile handsets, {n} laptops running betting panels and cash of Rs.{amount} were seized. {p1} @ {alias1}, who operates the panel, disclosed that accounts are settled through {p2} and that the master identity is controlled by {p3} from {foreign_city}.",
    ],
    "DEFAULT": [
        "It is alleged that the accused persons, namely {p1} @ {alias1}, {p2} and {p3}, in furtherance of a common intention, committed the offence at {area}, {city} on {date}. A sum of Rs.{amount} is stated to be involved. Mobile numbers {phone1} and {phone2} have been placed under technical surveillance and account {account1} of {bank1} has been frozen.",
        "The complaint discloses that on {date} at about {time} hrs, {p1} @ {alias1} along with {p2} and {p3} committed the offence within the jurisdiction of {ps} Police Station at {area}, {city}. The loss has been assessed at Rs.{amount}. A vehicle bearing {plate} used in the commission of the offence has been seized and technical analysis of {phone1} has been sought.",
        "Enquiry conducted by the {agency} discloses the involvement of {p1}, r/o {area}, {city}, along with {p2} of {area2}, {city2}, in the commission of the offence on {date}. Transactions aggregating Rs.{amount} between account {account1} of {bank1} and account {account2} of {bank2} are under examination. {p3} is stated to have facilitated the arrangement.",
    ],
}

SURVEILLANCE_TEMPLATES = [
    "Subject {p1} @ {alias1} was kept under discreet watch on {date} from {time} hrs. Subject left his residence at {area}, {city} in {a_vehicle} bearing {plate} and proceeded towards {area2}. At {time2} hrs the subject met {p2} at a {place_type} for approximately {mins} minutes. A bag was observed being handed over. Subject thereafter used a handset bearing number {phone1} for a brief call before switching it off.",
    "Static surveillance was maintained on the {place_type} at {area}, {city} on {date}. {p1}, {p2} and one unidentified person arrived separately between {time} and {time2} hrs. Photographic record has been obtained. A vehicle bearing {plate} registered in the name of {p3} remained parked outside for {mins} minutes.",
    "Technical surveillance on number {phone1} (subscriber: {p1}) shows {n} calls to {phone2} between {date} and {date2}, with a marked spike in the {hours} hours preceding the incident reported vide {fir}. The number went permanently silent thereafter, indicating discard of the SIM.",
    "Source reports that {p1} @ {alias1} has shifted base from {city} to {city2} and is presently coordinating operations through {p2}. Payments are stated to be routed via an angadia operating from {area}. Source graded {rel}{cred}.",
]

INTEL_NOTE_TEMPLATES = [
    "Assessment: {p1} @ {alias1} continues to exercise operational control over the {syn_label} despite being lodged in judicial custody. Instructions are relayed through {p2}, who visits as a legal representative. The financial arm is handled by {p3}, believed to be operating out of {foreign_city}. Confidence: {conf}.",
    "Note: A convergence is observed between the {syn_label} and the {syn_label2}. {p1}, previously assessed as a peripheral actor, is now placed as a common conduit -- he has received funds from {p2} of the former and passed instructions to {p3} of the latter. This linkage requires corroboration before it is treated as established. Confidence: {conf}.",
    "Alert: Unusual movement of funds noted in accounts controlled by {p1}. {n} deposits, each just below the reporting threshold, were made across {n_branches} branches of {bank1} in {days_short} days, aggregating Rs.{amount}. The pattern is consistent with structuring. Confidence: {conf}.",
    "Source reports that a consignment of {contraband} is likely to move from {city} to {city2} within {days_short} days. {p1} is expected to arrange transport and {p2} will receive it. The vehicle is likely to be {a_vehicle}. Corroboration pending. Confidence: {conf}.",
    "Observation: handset IMEI associated with {p1} was found active with a second SIM subsequently subscribed in the name of {p2}. Both numbers show overlapping cell-site presence at {area}, {city}. This indicates handset sharing or identity substitution. Confidence: {conf}.",
]

OCCUPATIONS = ["builder", "jeweller", "transporter", "chemist", "hotelier", "trader",
               "contractor", "commission agent", "scrap dealer", "money changer",
               "travel agent", "shopkeeper", "farmer", "real-estate broker"]

CAVITIES = ["fuel tank", "side panel", "false floor", "spare wheel", "dashboard",
            "seat lining", "LPG cylinder", "consignment of onions", "tyre tube"]

CONFIDENCE_LEVELS = ["LOW", "MODERATE", "HIGH"]

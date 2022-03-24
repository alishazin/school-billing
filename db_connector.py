
def initialize_database(dbObj, dbCursor):

    dbCursor.execute('CREATE DATABASE billing_software')
    dbCursor.execute('USE billing_software')
    dbCursor.execute("""CREATE TABLE productdetails (
        id INT PRIMARY KEY,
        name VARCHAR(30) UNIQUE NOT NULL,
        unit VARCHAR(6) NOT NULL,
        price float NOT NULL,
        stock float NOT NULL,
        CONSTRAINT check_unit CHECK (unit = 'packet' OR unit = 'kg')
    )""")
    dbCursor.execute("""CREATE TABLE backupproductdetails (
        id INT PRIMARY KEY,
        name VARCHAR(30) NOT NULL,
        unit VARCHAR(6) NOT NULL,
        price float NOT NULL
    )""")
    dbCursor.execute("""CREATE TABLE billdateandcustomertracker (
        bill_id INT PRIMARY KEY,
        date DATE NOT NULL,
        cus_id INT NOT NULL
    )""") 
    dbCursor.execute("""CREATE TABLE bill (
        bill_id INT NOT NULL,
        product_id INT NOT NULL,
        quantity float NOT NULL,
        price float NOT NULL,
        FOREIGN KEY (bill_id) REFERENCES billdateandcustomertracker(bill_id)
    )""")
    dbCursor.execute("""CREATE TABLE pricetracker (
        product_id INT NOT NULL,
        price float NOT NULL,
        date DATE NOT NULL
    )""")
    dbCursor.execute("""CREATE TABLE customerdetails (
        cus_id INT AUTO_INCREMENT PRIMARY KEY,
        contact_no VARCHAR(15) UNIQUE,
        name VARCHAR(30) NOT NULL,
        location VARCHAR(50) NULL,
        remaining_money float NOT NULL DEFAULT '0'
    )""")
    dbObj.commit()
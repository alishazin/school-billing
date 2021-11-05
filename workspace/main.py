from prettytable import PrettyTable
import matplotlib.pyplot as plt
import mysql.connector as conn
import os
import csv
import pickle
import time

import db_connector

def log_in(username, password): 
    """ Serves as a login interface. """

    # trying to login with the given details
    try:
        global DB_OBJECT
        DB_OBJECT = conn.connect(
            username=username,
            password=password
        )

    # if failed due to incorrect username or password, respond to the user with an error message
    except conn.errors.ProgrammingError:
        print("Access Denied, Can be due to Incorrect Username or Password")
        time.sleep(2)

    # if failed due to some other reason, print the error message given by the interpreter
    except Exception as error_details:
        print(f'\n{error_details}')

    # if successful, check whether the current user is new or not
    else:
        global DB_CURSOR
        DB_CURSOR = DB_OBJECT.cursor()
        check_if_new_user()

def check_if_new_user():
    """ Used to check whether the current user is a new one or not """

    # tring to connect to an existing databasem (works if the user is not new) 
    try:
        DB_CURSOR.execute('USE billing_software')

        # checking if table `productdetails` is empty
        if get_latest_id_in_table_productdetails() == 0:
            print('\nAssume that you are a new user, So lets start by adding a product.')
            enter_product_details()

        else:
            home_page()

    # Catching the error, if not, it can crash files related to application.
    except KeyboardInterrupt:
        DB_OBJECT.close()
        print('\nExiting..')
        time.sleep(1)

    # attempt failed as the database doesnt exist (as the user is a new one)
    except conn.errors.ProgrammingError:
        with open('cache/product_count.bin','wb') as file:
            pickle.dump(0, file)
            
        db_connector.initialize_database(DB_OBJECT, DB_CURSOR)
        create_readme_file()
        print('\nAssume that you are a new user, So lets start by adding a product.')
        enter_product_details()
    except Exception as error:
        print(error)
        print('Unknown error')

def create_readme_file():
    """ Creating and writing to a .txt file about warning not to corrupt files """

    with open('cache/README.txt','w') as file:
        file.write('Dont make any changes to the files in this directory. Renaming, replacing or deleting them can crash the application.')

def enter_product_details():
    """ Interface to recieve product details from the user after checking for wrong data. """

    while True:
        product_name = input('\nEnter Product Name : ')
        if len(str(product_name)) == 0:
            print('\nError: Field was left empty..')
            continue

        product_unit = input('\nEnter Product Unit ( packet / kg ) : ')
        if len(str(product_unit)) == 0:
            print('\nError: Field was left empty..')
            continue
        elif product_unit not in ['packet', 'kg']:
            print("\nInvalid value for unit. Select one of either 'packet' or 'kg'")
            continue

        try:
            product_price = float(input('\nEnter Product Price Per Unit (in ₹) : '))
        except:
            print('\nError: Product Price should be a numeric value')
            continue
        else:
            if product_price <= 0:
                print('\nError: Product Price should be a positive number')
                continue
            else:
                try:
                    product_stock = float(input('\nEnter The Product Primary Stock : '))
                except:
                    print('\nError: Product Stock should be a numeric value')
                    continue
                else:
                    if product_stock <= 0:
                        print('\nError: Product Stock should be a positive number')
                        continue
                    elif product_unit == 'packet' and int(product_stock) != float(product_stock):
                        print('\nError: Product Meant to be sold in packets should not have non-integer Stock value')
                        continue
                    else:
                        break

    enter_product_details_into_database(product_name,product_unit,product_price,product_stock)

def enter_to_price_tracker(id, price):
    """ Function to write to table `pricetracker` """
  
    DB_CURSOR.execute(f"SET @pro_price = {float(price)}")
    DB_CURSOR.execute(f"INSERT INTO pricetracker VALUES({id},@pro_price,current_date())")

def enter_product_details_into_database(name, unit, price, stock):
    """ Function for inserting product details into the table `productdetails` """

    latestID = int(get_latest_id_in_table_productdetails())

    # setting mysql variables to prevent SQL Injection.
    DB_CURSOR.execute(f"SET @pro_name = '{name}'")
    DB_CURSOR.execute(f"SET @pro_unit = '{unit}'")
    DB_CURSOR.execute(f"SET @pro_price = {float(price)}")
    DB_CURSOR.execute(f"SET @pro_stock = {float(stock)}")

    try:
        DB_CURSOR.execute(f"INSERT INTO productdetails VALUES({latestID + 1},@pro_name,@pro_unit,@pro_price,@pro_stock)")
        enter_to_price_tracker(int(latestID + 1), price)
        DB_OBJECT.commit()

    # if product name is getting repeated
    except conn.errors.IntegrityError:
        print(f"\nError: Product Name '{name}' is repeated.")
        enter_product_details()

    # if failed due to some other reason, print the error message given by the interpreter
    except Exception as error_details:
        print(f'\n{error_details}')

    else:
        with open('cache/product_count.bin','wb') as file:
            latestID = pickle.dump(int(latestID + 1), file)

        print(f"\nProduct '{name}' added successfully..")
        home_page()

def get_latest_id_in_table_productdetails():
    """ Every column in the table `productdetails` has a unique `id`, This function returns the latest id if table is not empty. But if the table is empty, it returns `0` """

    latestID = 0
    DB_CURSOR.execute('SELECT id FROM productdetails')
    result = DB_CURSOR.fetchall()
    if len(result) == 0:
        pass
    else:
        with open('cache/product_count.bin','rb') as file:
            latestID = pickle.load(file)
    return latestID

def show_product_details_in_terminal():
    """ Function to view all the product details using `prettytable`. """

    productTable = PrettyTable(['ID','Product Name','Unit','Price', 'Stock'])
    DB_CURSOR.execute("SELECT * FROM productdetails")
    result = DB_CURSOR.fetchall()
    for i in result:
        productTable.add_row([i[0],i[1],i[2],i[3],i[4]])
    print(f'\n--Product Details--\n\n{productTable}')
    go_back_to_home_page()

def go_back_to_home_page():
    """ 
    Function to go back to home page. `Note:` This function print less string so that user can have a look at the latest message (usually error message), 
    especially if using a smaller screen 
    """

    input('\nPress Enter to go back to Home Page : ')
    home_page()

def show_product_details_in_csv():
    """ Function to view all the product details using `csv` and `os`. """

    # selecting data from database
    DB_CURSOR.execute("SELECT * FROM productdetails")
    result = DB_CURSOR.fetchall()

    # chance of error if the file `product_details.csv` is open
    try:
        with open('cache/product_details.csv','w') as file:
            csv_writer = csv.writer(file)
            csv_writer.writerow(['ID','Product Name','Unit','Price','Stock'])

            for i in result:
                csv_writer.writerow(i)
                
        # opening `product_details.csv`
        os.popen('cache\\product_details.csv')

        home_page()

    # Catching the error, if not, it can crash files related to application.
    except KeyboardInterrupt:
        DB_OBJECT.close()
        print('\nExiting..')
        time.sleep(1)

    except:
        print("\n'product_details.csv' is currently open, close it and try again")
        go_back_to_home_page()

def delete_product_details():
    """ Function to delete Product Details """

    idDelete = input('\nEnter the ID of the product to delete ( to cancel enter nothing ): ')
    if len(idDelete) == 0:
        home_page()
    else:
        if check_for_delete(idDelete) == 'valueError':
            print('\nError: ID should be a numeric value')
            go_back_to_home_page()
        elif check_for_delete(idDelete) == False:
            print('\nError: ID does not exist')
            go_back_to_home_page()
        else:
            stockRemaining = get_product_stock_from_id(int(idDelete))
            confirmation = input(f"\nID '{idDelete}' has '{stockRemaining}' stocks remaining. Are you sure about deleting ? (Yes / No) : ")
            if confirmation.lower() == 'yes':
                add_details_to_backup(int(idDelete))
                DB_CURSOR.execute(f"SET @id = {int(idDelete)}")
                DB_CURSOR.execute("DELETE FROM productdetails WHERE id = @id")
                delete_from_price_tracker(int(idDelete))
                DB_OBJECT.commit()

                print(f"\nID '{idDelete}' is Successfully Deleted.")
            else:
                print(f"\nID '{idDelete}' is Not Deleted.")

            go_back_to_home_page()

def get_product_stock_from_id(id):
    """ Returns `stock` of the product by recieving `product_id` """

    DB_CURSOR.execute(f"SELECT stock FROM productdetails WHERE id = '{id}'")
    result = DB_CURSOR.fetchall()
    return float(result[0][0])

def delete_from_price_tracker(id):
    """ Function to delete from table `pricetracker` """
    
    DB_CURSOR.execute(f"SET @id = {id}")
    DB_CURSOR.execute("DELETE FROM pricetracker WHERE product_id = @id")

def add_details_to_backup(id):
    """ Entering data into `backupproductdetails` """

    DB_CURSOR.execute(f"SELECT * FROM productdetails WHERE id = {id}")
    result = DB_CURSOR.fetchall()
    name = result[0][1]
    unit = result[0][2]
    price = result[0][3]
    DB_CURSOR.execute(f"INSERT INTO backupproductdetails VALUES({id},'{str(name)}','{str(unit)}',{float(price)})")
    DB_OBJECT.commit() 

def check_for_delete(id):
    """ 
    Function to check whether the argument `id` exist in the table `productdetails`. Returns `valueError` if id is not numeric, 
    `False` if `id` does not exist, `True` if `id` does exist
    """

    try:
        idLocal = int(id)
    except ValueError:
        return 'valueError'
    else:
        DB_CURSOR.execute(f"SET @id = '{id}'")
        DB_CURSOR.execute("SELECT name FROM productdetails WHERE id = @id")
        result = DB_CURSOR.fetchall()
        check = True
        if len(result) == 0:
            check = False

        return check

def check_limit_remove():
    """ Checking whether the `productdetails` have more than one record. Raise an error if there is only one record. """
    DB_CURSOR.execute('SELECT count(id) FROM productdetails')
    if list(DB_CURSOR.fetchall())[0][0] == 1:
        input('\nError: Minimum Number of Product allowed is 1, (Press Enter to continue) : ')
        home_page()
    else:
        delete_product_details()

def show_backup_product_details_in_csv():
    """ Function to view all the backup product details using `csv` and `os`. """

    # selecting data from database
    DB_CURSOR.execute("SELECT * FROM backupproductdetails")
    result = DB_CURSOR.fetchall()

    # chance of error if the file `backup_product_details.csv` is open
    try:
        with open('cache/backup_product_details.csv','w') as file:
            csv_writer = csv.writer(file)
            csv_writer.writerow(['ID','Product Name','Unit','Price'])

            for i in result:
                csv_writer.writerow(i)
                
        # opening `backup_product_details.csv`
        os.popen('cache\\backup_product_details.csv')

        home_page()
    
    # Catching the error, if not, it can crash files related to application.
    except KeyboardInterrupt:
        DB_OBJECT.close()
        print('\nExiting..')
        time.sleep(1)

    except:
        print("\n'backup_product_details.csv' is currently open, close it and try again")
        go_back_to_home_page()

def show_backup_product_details_in_terminal():
    """ Function to view all the backup product details using `prettytable`. """

    productTable = PrettyTable(['ID','Product Name','Unit','Price'])
    DB_CURSOR.execute("SELECT * FROM backupproductdetails")
    result = DB_CURSOR.fetchall()
    for i in result:
        productTable.add_row([i[0],i[1],i[2],i[3]])
    print(f'\n--Backup Product Details--\n\n{productTable}')
    go_back_to_home_page()

def enter_cus_details():
    """ User Interface for entering customer details for the bill. If new customer, stored in a GLOBAL variable(dictionary). """

    while True:
        conNo = input("\nEnter the Contact Number of the Customer : ")
        if len(conNo) > 15:
            print('\nError: Contact Number should be less than 15')
            continue
        elif conNo[0].strip() == '0': 
            print("\nError: Contact Number Shouldn't Start With Zero")
            continue
        elif conNo.isnumeric():
            if check_if_existing_customer(conNo):
                conNo2, cusName, cusLoc, remainingMoney = get_customer_details_from_con_no(conNo)
            else:
                conNo2, cusName, cusLoc, remainingMoney = add_new_customer(conNo)
            break
        else:
            print("\nError: Invalid Contact Number")
            continue

    edit_global_var_customer_details(conNo2, cusName, cusLoc, remainingMoney)
    enter_bill()

def edit_global_var_customer_details(number, name, location, remaining):
    """ Function to initialize the global variable `CUSTOMER_DETAILS` """

    global CUSTOMER_DETAILS
    CUSTOMER_DETAILS = {
        'number' : number,
        'name' : name,
        'location' : location,
        'remaining' : remaining
    }

def get_cus_id_from_con_no(number):
    """ Function to return cus_id after providing Contact Number """

    DB_CURSOR.execute(f"SELECT cus_id FROM customerdetails WHERE contact_no = '{number}'")
    result = DB_CURSOR.fetchall()
    return result[0][0]

def get_customer_details_from_cus_id(cusId, instance = 0):
    """ Function to return customer details after providing cus_id """

    DB_CURSOR.execute(f"SET @id = {cusId}")
    DB_CURSOR.execute("SELECT * FROM customerdetails WHERE cus_id = @id")
    result = DB_CURSOR.fetchall()
    if instance == 1:
        if len(result) == 0:
            return ['', '', '', '', '']
        else:
            return [result[0][0], result[0][1], result[0][2], result[0][3], result[0][4]]
    else:
        return result[0][1], result[0][2], result[0][3], result[0][4]

def get_customer_details_from_con_no(number, instance = 0):
    """ Function to return customer details after providing Contact Number """

    DB_CURSOR.execute(f"SET @con_no = {number}")
    DB_CURSOR.execute("SELECT * FROM customerdetails WHERE contact_no = @con_no")
    result = DB_CURSOR.fetchall()
    if instance == 1:
        if len(result) == 0:
            return ['', '', '', '', '']
        else:
            return [result[0][0], result[0][1], result[0][2], result[0][3], result[0][4]]
    else:
        return result[0][1], result[0][2], result[0][3], result[0][4]

def add_new_customer(conNo):
    """ User Interface to add a new customer. """

    print(f"\nUser with Contact No: {conNo} doesn't exist. So, we will add a new one. ")

    while True:
        cusName = input("\nEnter the Customer Name : ")
        if len(cusName.strip()) == 0:
            print("\nError: Invalid Customer Name")
            continue
        elif len(cusName) > 30:
            print('\nError: Customer Name should be less than 30 characters')
        else:
            cusLoc = input("\nEnter the Customer Location (optional) : ")
            if len(cusLoc.strip()) == 0:
                cusLoc = None
            elif len(cusLoc) > 40:
                print('\nError: Customer Location should be less than 40 characters')
                continue
            break

    if cusLoc == None:
        DB_CURSOR.execute(f"INSERT INTO customerdetails(contact_no, name) VALUES('{int(conNo)}','{cusName}')")
    else:
        DB_CURSOR.execute(f"INSERT INTO customerdetails(contact_no, name, location) VALUES('{int(conNo)}','{cusName}','{cusLoc}')")
    DB_OBJECT.commit()

    return conNo, cusName, cusLoc, 0

def check_if_existing_customer(number):
    """ Function to check whether a customer exist with the `passed` contact number """

    DB_CURSOR.execute(f"SELECT name FROM customerdetails WHERE contact_no = '{number}'")
    result = DB_CURSOR.fetchall()
    if len(result) == 0:
        return False
    else:
        return True

def enter_bill():
    """ User Interface for entering bill along with a little error catching """

    billList = []
    count = 1
    while True:
        tempList = []
        product = input(f'\nEnter the product name({count}) : ')
        if check_product_existance(product):
            tempList.append(product)
            quantity = input(f'\nEnter the Quantity({count}) : ')
            quantityCheck = quantity_check(product, quantity)
            if quantityCheck == True:
                tempList.append(quantity)
                stockRemainingCheck = stock_remaining_check(product, float(quantity))
                if stockRemainingCheck == True:
                    confirmation = input("\nEnter '1' to continue adding to the bill, Enter '0' to cancel the bill, Enter something else to finalise the bill : ")
                    billList.append(tempList)
                    if confirmation == '1':
                        count += 1
                        continue
                    elif confirmation == '0':
                        info = 'cancel'
                        break
                    else:
                        info = None
                        break
                else:
                    print(f'\n{stockRemainingCheck}')
                    confirmation2 = input("\nEnter '1' to continue adding to the bill, Enter '0' to cancel the bill, Enter Something else to finalise the bill : ")
                    if confirmation2 == '1':
                        continue
                    elif confirmation2 == '0':
                        info = 'cancel'
                        break 
                    else:
                        info = None
                        break 
            else:
                print(quantityCheck)
                continue
        else:
            print('\nError: Invalid Product name')
            continue
    
    if info == 'cancel':
        print('\nBill Cancelled..')
        go_back_to_home_page()
    else:
        if len(billList) > 0:
            sort_bill(billList)
        else:
            go_back_to_home_page()

def stock_remaining_check(name, quantity):
    """ Function to check whether the product is out of stock. Return `True` if everything is fine, else return a proper error message """

    DB_CURSOR.execute(f"SELECT stock FROM productdetails WHERE BINARY(name) = '{name}'")
    stockRemaining = float((DB_CURSOR.fetchall())[0][0])
    stockAfter = stockRemaining - quantity

    if stockAfter < 0:
        return f"Product '{name}' is out of stock. Remaining stock is '{stockRemaining}'"
    else:
        return True
            
def quantity_check(name, quantity):
    """ Function to check whether the argument `quantity` value is valid or not. """

    try:
        a = float(quantity)
    except ValueError:
        return '\nError: Invalid Input.'
    else:
        if a <= 0:
            return '\nError: Quantity cant be zero or less than zero.'
        elif packet_check(name):
            if float(a) != int(a):
                return '\nError: Products meant to be sold as packets should not have non-integer quantity.'
            else:
                return True
        elif packet_check(name) == False:
            return True

def packet_check(name):
    """ Function to check whether the argument `name` is of unit packet or not. """

    DB_CURSOR.execute(f"SET @name = '{name}'")
    DB_CURSOR.execute(f"SELECT unit FROM productdetails WHERE BINARY(name) = @name")
    result = DB_CURSOR.fetchall()
    if result[0][0] == 'packet':
        return True
    else:
        return False

def sort_bill(bill):
    """ Sorting the bill by concatinating the `quantity` of all the repeated `product names` """

    billFinal = {}
    for i in bill:
        try:
            billFinal[i[0]] += float(i[1])
        except: 
            billFinal[i[0]] = float(i[1])
    add_bill_to_database(billFinal)

def add_bill_to_database(bill_dict):
    """ Adding the bill onto the database. To the table `bill` """

    billWithProductId = []
    for name,quantity in bill_dict.items():
        tempList = []
        productId = replace_name_with_product_id(name)
        tempList.append(productId)
        tempList.append(quantity)
        tempList.append(get_product_price_from_id(productId))
        billWithProductId.append(tempList)
    del bill_dict

    reduce_stock_product(billWithProductId)
    latestID = get_latest_bill_id()

    # Inserting to the table `billdateandcustomertracker`
    DB_CURSOR.execute(f"INSERT INTO billdateandcustomertracker VALUES({int(latestID + 1)},current_date(),'{get_cus_id_from_con_no(CUSTOMER_DETAILS['number'])}')")
    DB_OBJECT.commit()

    # Inserting to the table `bill`
    for i in billWithProductId:
        DB_CURSOR.execute(f"INSERT INTO bill VALUES({int(latestID + 1)},{int(i[0])},{float(i[1])},{float(i[2])})")
    DB_OBJECT.commit()

    # Incrementing to the file `bill_count.bin`
    with open('cache/bill_count.bin','wb') as file:
        pickle.dump(int(latestID + 1), file)

    generate_bill_with_price(billWithProductId, int(latestID + 1), 'new')
    go_back_to_home_page()

def reduce_stock_product(bill):
    """ Function to reduce the stock from `productdetails` table, during the billing process """

    for i in bill:
        DB_CURSOR.execute(f"SELECT stock FROM productdetails WHERE id = '{i[0]}'")
        stockRemaining = float((DB_CURSOR.fetchall())[0][0])
        DB_CURSOR.execute(f"UPDATE productdetails SET stock = '{stockRemaining - i[1]}' WHERE id = '{i[0]}'")

    DB_OBJECT.commit()

def generate_bill_with_price(bill, billId, status = 'old'):
    """ Recieving the bill in the form of `list` as `bill` and returning a `list` with all the values needed to print the bill onto a `.txt` file """

    billToPrint = []
    for i in bill:
        tempList = []
        tempList.append(i[0])
        tempList.append(get_product_name_from_id(i[0]))
        tempList.append(i[2])
        tempList.append(i[1])
        tempList.append(float(i[2] * i[1]))
        billToPrint.append(tempList)

    create_bill_as_table(billToPrint, billId, status)

def create_bill_as_table(billList, billID, status):
    """ Recieving a finished bill in the `list` datatype and creating a proper table using `prettytable` to view the bill """
    
    billTable = PrettyTable(['Product ID','Product Name','Price Per Unit','Quantity','Total'])
    billTotal = 0
    for i in billList:
        billTotal += float(i[4])
        billTable.add_row([i[0],check_backup_or_not(i[0],i[1]),i[2],i[3],i[4]])

    if status == 'new':
        while True:
            moneyPaid = input(f"\nTotal Cost of the Current Purchase = {billTotal}.\nDue Amount including this bill for the Customer '{CUSTOMER_DETAILS['name']}' = {float(CUSTOMER_DETAILS['remaining']) + billTotal}.\nEnter the money that customer had paid (Enter Nothing if '{billTotal}' is paid) : ")
            if len(moneyPaid.strip()) == 0:
                moneyLeft = (float(CUSTOMER_DETAILS['remaining']) + billTotal) - float(billTotal)
                DB_CURSOR.execute(f"UPDATE customerdetails SET remaining_money = '{moneyLeft}' WHERE contact_no = '{CUSTOMER_DETAILS['number']}'")
                DB_OBJECT.commit()
                break
            elif check_if_money(moneyPaid) == False:
                print("\nError: Invalid Input.")
                continue
            else:
                moneyLeft = (float(CUSTOMER_DETAILS['remaining']) + billTotal) - float(moneyPaid)
                if moneyLeft >= 0:             
                    DB_CURSOR.execute(f"UPDATE customerdetails SET remaining_money = '{moneyLeft}' WHERE contact_no = '{CUSTOMER_DETAILS['number']}'")
                    DB_OBJECT.commit()
                    break
                elif moneyLeft < 0:
                    print("\nError: Money Paid by the Customer has Exceeded the Due Money.")
                    continue

    show_bill_in_txt_file(billTable, billID, billTotal)

def check_if_money(number):
    """ Function return True if argument is a proper number. else return False """

    if number.strip() == '':
        return True

    try:
        float(number)
    except:
        return False
    else:
        return True

def check_backup_or_not(id,name):
    """ Function to check whether the recieved `product_id` is deleted or not """
    
    DB_CURSOR.execute(f"SET @id = {id}")
    DB_CURSOR.execute("SELECT name FROM backupproductdetails WHERE id = @id")
    result = DB_CURSOR.fetchall()
    check = True
    if len(result) == 0:
        check = False

    if check == False:
        return str(name)
    else:
        return f"{name}(Deleted)"

def show_bill_in_txt_file(billTable, billId, billTotal):
    """ Writing the `bill`, `bill ID` and `Total Cost` onto a `.txt` file """

    # chance of error if the file `bill.txt` is open
    try:
        with open('cache/bill.txt','w') as file:
            file.write(f"Bill ID : {billId}\nDate : {get_date_from_bill_id(billId)}\nContact No : {CUSTOMER_DETAILS['number']}\nCustomer Name : {CUSTOMER_DETAILS['name']}\n\n{str(billTable)}\n\nTotal Cost ----------> {float(billTotal)}")
        os.popen('cache\\bill.txt')
        print('\nBill Generated Successfully')

    except Exception as error:
        print(f'\nError: {error}')

def get_date_from_bill_id(billId):
    DB_CURSOR.execute(f"SELECT date FROM billdateandcustomertracker WHERE bill_id = {billId}")
    return str((DB_CURSOR.fetchall())[0][0])

def get_product_price_from_id(id):
    """ Returns `price` of the product by recieving `product_id` """

    DB_CURSOR.execute(f"SELECT price FROM productdetails WHERE id = '{id}'")
    result = DB_CURSOR.fetchall()
    return float(result[0][0])

def get_product_name_from_id(id, instance = 0):
    """ Returns `name` of the product by recieving `product_id` """

    backup = False
    DB_CURSOR.execute(f"SELECT name FROM productdetails WHERE id = '{id}'")
    result = DB_CURSOR.fetchall()
    if len(result) == 0:
        DB_CURSOR.execute(f"SELECT name FROM backupproductdetails WHERE id = '{id}'")
        result = DB_CURSOR.fetchall()
        backup = True
    else:
        pass
    if instance == 1 and backup == True:
        return f"{result[0][0]}(Del)"
    else:
        return str(result[0][0])

def get_latest_bill_id():
    """ Returns the latest `Bill ID` from the file `bill_count.bin` """

    latestID = 0
    DB_CURSOR.execute("SELECT * FROM bill")
    if len(DB_CURSOR.fetchall()) == 0:
        pass
    else:
        with open('cache/bill_count.bin','rb') as file:
            latestID = pickle.load(file)
    return int(latestID)

def replace_name_with_product_id(name):
    """ Function to replace the `product name` with its `id`, by checking from `productdetails` tables """

    DB_CURSOR.execute(f"SELECT id FROM productdetails WHERE name = '{str(name)}'")
    return (DB_CURSOR.fetchall())[0][0]

def check_product_existance(name):
    """ Function to check whether the given product exist or not. Returns `True` if exist and `False` if not """

    DB_CURSOR.execute(f"SET @name = '{name}'")
    DB_CURSOR.execute("SELECT id FROM productdetails WHERE BINARY(name) = @name")
    result = DB_CURSOR.fetchall()
    check = True
    if len(result) == 0:
        check = False
    return check

def view_latest_bill():
    """ Viewing the latest bill generated """

    latestBillID = get_latest_bill_id()
    if latestBillID == 0:
        print("\nError: No Bills Are Added Yet...")
        go_back_to_home_page() 
    else:
        billWithProductId = get_bill_using_bill_id(latestBillID)
        generate_bill_with_price(billWithProductId ,latestBillID)
        go_back_to_bill_view()

def get_cus_id_from_bill_id(billId):
    """ Function to get cus_id from bill_id from table `billdateandcustomertracker` """

    DB_CURSOR.execute(f"SELECT cus_id FROM billdateandcustomertracker WHERE bill_id = '{billId}'")
    result = DB_CURSOR.fetchall()
    return result[0][0]

def get_bill_using_bill_id(billId):
    """ Getting the bill details from `bill` table according to the recieved `Bill ID` """

    cusNumber, cusName, cusLocation, cusRemaining = get_customer_details_from_cus_id(get_cus_id_from_bill_id(billId))
    edit_global_var_customer_details(cusNumber, cusName, cusLocation, cusRemaining)

    DB_CURSOR.execute(f"SELECT product_id,quantity,price FROM bill WHERE bill_id = {billId}")
    result = DB_CURSOR.fetchall()
    billWithProductId = []
    for i in result:
        tempList = []
        tempList.append(i[0])
        tempList.append(i[1])
        tempList.append(i[2])
        billWithProductId.append(tempList)

    return billWithProductId

def search_bill_using_id():
    """ User Interface for entering the `Bill ID` to search for, along with a formal error catching """

    latestBillID = get_latest_bill_id()
    if latestBillID == 0:
        print("\nError: No Bills Are Added Yet...")
        go_back_to_home_page() 
    else:
        billId = input('\nEnter the Bill ID to search for : ')
        try:
            billId = float(billId)
        except:
            print('\nError: Invalid Input')
            search_bill_using_id()
        else:
            if billId != int(billId):
                print('\nError: Bill ID should be an integer')
                search_bill_using_id()
            elif billId <= 0:
                print('\nError: Bill ID cant be zero or less than zero.')
                search_bill_using_id()
            elif billId > latestBillID:
                print('\nError: A Bill with the particular Bill ID does not exist.')
                search_bill_using_id()
            else:
                bill = get_bill_using_bill_id(billId)
                generate_bill_with_price(bill, billId)
                go_back_to_bill_view()

def edit_product_price():
    """ User Interface to enter ID for editing its price """

    idEdit = input('\nEnter the ID of the product to edit ( to cancel enter nothing ): ')
    if len(idEdit) == 0:
        home_page()
    else:
        if check_for_delete(idEdit) == 'valueError':
            print('\nError: ID should be a numeric value')
            edit_product_price()
        elif check_for_delete(idEdit) == False:
            print('\nError: ID does not exist')
            edit_product_price()
        else:
            edit_price_interface(int(idEdit))

def edit_price_interface(id):
    """ User Interface to enter the new price replacing the old one """

    oldPrice = float(get_product_price_from_id(id))
    try:
        priceEdit = float(input(f"\nPrice of the product with ID '{id}' and Name '{get_product_name_from_id(id)}' is '{oldPrice}'. Enter the New Price: "))
    except:
        print('\nError: Product Price should be a numeric value')
        edit_price_interface(id)
    else:
        if priceEdit < 0:
            print('\nError: Product Price should be a positive number')
            edit_price_interface(id)
        elif priceEdit == oldPrice:
            no_changes_made()
        else:
            edit_price_database(id,priceEdit)

def no_changes_made():
    """ Function called if the edited price is same as the old(latest) one """

    print("\nNo Changes Made")
    go_back_to_home_page()
    
def edit_price_database(id, priceEdit):
    """ Making changes(UPDATING) in the database, table `productdetails` while editing price """

    DB_CURSOR.execute(f"UPDATE productdetails SET price = {priceEdit} WHERE id = {id}")
    enter_to_price_tracker(id, priceEdit)
    DB_OBJECT.commit()
    print("\nPrice Edited Successfully")
    go_back_to_home_page()

def go_back_to_bill_view():
    """ 
    Function to go back to bill view. `Note:` This function print less string so that user can have a look at the latest message (usually error message), 
    especially if using a smaller screen 
    """

    input('\nPress Enter to go back to Bill View : ')
    bill_view_page()

def go_back_to_customer_view():
    """ 
    Function to go back to customer view. `Note:` This function print less string so that user can have a look at the latest message (usually error message), 
    especially if using a smaller screen 
    """

    input('\nPress Enter to go back to Customer View Page : ')
    customer_view_page()

def bill_view_page():
    """ Serves as a Bill View Page. """

    print("\n---Bill View---\n\n1. View the latest bill.\n2. Search using Bill ID.\n3. Go Back to Home Page.")
    option = input('\nEnter a Valid Option : ')

    if option == '1':
        view_latest_bill()
    elif option == '2':
        search_bill_using_id()
    elif option == '3':
        home_page()
    else:
        print('\nError: Invalid Option')
        bill_view_page()

def price_details_interface():
    """ User Interface to enter ID for viewing its price details """

    idPlot = input('\nEnter the ID of the product to view price details ( to cancel enter nothing ): ')
    if len(idPlot) == 0:
        graph_page()
    else:
        if check_for_delete(idPlot) == 'valueError':
            print('\nError: ID should be a numeric value')
            price_details_interface()
        elif check_for_delete(idPlot) == False:
            print('\nError: ID does not exist')
            price_details_interface()
        else:
            plot_price_details(idPlot)

def plot_price_details(id):
    """ Plotting graph using `matplotlib`, graph for viewing price variation of a particular product """

    DB_CURSOR.execute(f"SET @id = {id}")
    DB_CURSOR.execute("SELECT * FROM pricetracker WHERE product_id = @id")
    result = DB_CURSOR.fetchall()
    if len(result) <= 1:
        print('\nError: Not enough data available to plot a graph')
        go_back_to_graph_page()
    else:
        print('\nPlotting..')
        x_axis = []
        y_axis = []
        count = 1
        for i in result:
            x_axis.append(f"{i[2]}({count})")
            y_axis.append(i[1])
            count += 1
        plt.title(f'(ID = {id}) {get_product_name_from_id(id)}', size='15', color='blue')
        plt.xlabel('Date', size='15', color='green')
        plt.ylabel('Price (₹)', size='15', color='green')
        plt.plot(x_axis, y_axis, color='red', marker='o', ms='10', mfc='green')
        plt.grid()

        print("\nApplication won't respond until you close the graph..")
        plt.show()

        go_back_to_graph_page()

def go_back_to_graph_page():
    """ 
    Function to go back to graph page. `Note:` This function print less string so that user can have a look at the latest message (usually error message), 
    especially if using a smaller screen 
    """

    input('\nPress Enter to go back to Graph Page : ')
    graph_page()

def most_sold_product_sorting():
    """ Analyzing and collecting data for plotting the graph based on most sold product """

    if get_latest_bill_id() == 0:
        print('\nError: No Bills are added yet.')
        go_back_to_graph_page()
    else:
        DB_CURSOR.execute("SELECT product_id, quantity FROM bill")
        result = DB_CURSOR.fetchall()
        quantity_count = {}
        for i in result:
            try:
                quantity_count[i[0]] += i[1]
            except:
                quantity_count[i[0]] = i[1]
        quantity_count_sorted = dict(sorted(quantity_count.items(),key= lambda x:x[1], reverse=True))
        del quantity_count
        if len(quantity_count_sorted) > 5:
            temp_dict = {}
            count = 0
            for key, value in quantity_count_sorted.items():
                if count < 5:
                    temp_dict[key] = value
                else:
                    break
                count += 1
            quantity_count_sorted = temp_dict
            del temp_dict
        
        x_axis = []
        y_axis = []
        for key, value in quantity_count_sorted.items():
            x_axis.append(f'{get_product_name_from_id(int(key), 1)}({key})')
            y_axis.append(float(value))

        plot_bar_graph(
            'Most Sold Products (Top 5)',
            'Product Name (ID)',
            'No. of Products Sold',
            x_axis,
            y_axis
        )  

def add_stock_interface():
    """ Interface for adding stock to existing products """
    
    idStock = input('\nEnter the id of the Product to Add Stock ( to cancel enter nothing ) : ')
    if len(idStock) == 0:
        go_back_to_home_page()
    else:
        if check_for_delete(idStock) == 'valueError':
            print('\nError: ID should be a numeric value')
            add_stock_interface()
        elif check_for_delete(idStock) == False:
            print('\nError: ID does not exist')
            add_stock_interface()
        else:
            try:
                stockToAdd = float(input('\nEnter the Value Adding to the Stock : '))
            except:
                print('\nError: Product Stock should be a numeric value')
                add_stock_interface()
            else:
                if stockToAdd <= 0:
                    print('\nError: Product Stock should be a positive number')
                    add_stock_interface()
                elif packet_check(get_product_name_from_id(idStock)) == True and int(stockToAdd) != float(stockToAdd):
                    print('\nError: Product Meant to be sold in packets should not have non-integer Stock value')
                    add_stock_interface()
                else:
                    add_stocks_to_database(idStock, stockToAdd)

def add_stocks_to_database(id, value):
    """ Function to update the database with the new stock value """

    exisitingStock = get_product_stock_from_id(id)
    DB_CURSOR.execute(f"UPDATE productdetails SET stock='{exisitingStock + value}' WHERE id = '{id}'")
    DB_OBJECT.commit()

    print(f"\nProduct Stock Updated to '{exisitingStock + value}' Successfully.")
    go_back_to_home_page()

def show_stock_alert():
    """ Function to see if there is any product running out of stock comparing to the value inputted """

    try:
        limitValue = float(input('\nEnter the Stock Limit ( To Check if Any Product is Running Out of Stock ) : '))
    except:
        print('\nError: Stock Limit should be a numeric value')
        show_stock_alert()
    else:
        if limitValue < 0:
            print('\nError: Stock Limit should be a positive number')
            show_stock_alert()
        else:
            DB_CURSOR.execute(f"SELECT id,name,stock FROM productdetails WHERE stock <= '{limitValue}'")
            result = DB_CURSOR.fetchall()

            stockAlertTable = PrettyTable(['ID','Product Name','Stock'])
            for i in result:
                stockAlertTable.add_row([i[0],i[1],i[2]])
            print(f'\n--Stock Alerts !--\n\n{stockAlertTable}')

            go_back_to_home_page()

def search_customer_using_con_no():
    """ Function to search for customer details using Customer Conatact Number """

    conNo = input("\nEnter the Contact Number To Search For : ")

    if len(conNo.strip()) == 0:
        print("\nError: Invalid Input")
        search_customer_using_con_no()
    else:
        customerTable = PrettyTable(['ID','Contact No','Name','Location', 'Remaining Amount'])
        customerTable.add_row(get_customer_details_from_con_no(conNo, 1))
        print(f'\n{customerTable}')
        go_back_to_customer_view()

def search_customer_using_name():
    """ Function to search for customer details using Customer Name """

    name = input("\nEnter the Name To Search For : ")

    if len(name.strip()) == 0:
        print("\nError: Invalid Input")
        search_customer_using_name()
    else:
        likeOrExact = input("\nEnter 0 for EXACT search, Enter 1 for LIKE(starting with) search or Enter 2 for LIKE(anywhere in the name) search : ")

        if likeOrExact.strip() == '0':
            DB_CURSOR.execute(f"SET @cus_name = '{name.lower()}'")
            DB_CURSOR.execute("SELECT * FROM customerdetails WHERE BINARY(LOWER(name)) = @cus_name")
            result = DB_CURSOR.fetchall()
            customerTable = PrettyTable(['ID','Contact No','Name','Location', 'Remaining Amount'])
            for i in result:
                customerTable.add_row([i[0],i[1],i[2],i[3],i[4]])
            print(f'\n{customerTable}')
            go_back_to_customer_view()

        elif likeOrExact.strip() == '1':
            DB_CURSOR.execute(f"SELECT * FROM customerdetails WHERE LOWER(name) LIKE '{name.lower()}%'")
            result = DB_CURSOR.fetchall()
            customerTable = PrettyTable(['ID','Contact No','Name','Location', 'Remaining Amount'])
            for i in result:
                customerTable.add_row([i[0],i[1],i[2],i[3],i[4]])
            print(f'\n{customerTable}')
            go_back_to_customer_view()

        elif likeOrExact.strip() == '2':
            DB_CURSOR.execute(f"SELECT * FROM customerdetails WHERE LOWER(name) LIKE '%{name.lower()}%'")
            result = DB_CURSOR.fetchall()
            customerTable = PrettyTable(['ID','Contact No','Name','Location', 'Remaining Amount'])
            for i in result:
                customerTable.add_row([i[0],i[1],i[2],i[3],i[4]])
            print(f'\n{customerTable}')
            go_back_to_customer_view()

        else:
            print("\nError: Invalid Input")
            search_customer_using_name()

def reduce_from_due_amount():
    """ Function to reduce from `remaining_money` column manually without printing a bill """

    conNo = input("\nEnter the Contact Number of the Customer to Reduce From : ")

    if conNo.isnumeric():
        cusDetails = get_customer_details_from_con_no(conNo, 1)
        if cusDetails[4] == '':
            print("\nError: Contact Number doesn't Exist")
            reduce_from_due_amount()
        else:
            print(f"\nCustomer '{cusDetails[2]}' has a due Amount of '{cusDetails[4]}'")
            reduceMoney = input("\nEnter the Amount that you Want to Reduce : ")
            if check_if_money(reduceMoney) and float(reduceMoney) >= 0:
                if float(reduceMoney) > float(cusDetails[4]):
                    print("\nError: Customer has Exceeded the Due Amount")
                    reduce_from_due_amount()
                else:
                    DB_CURSOR.execute(f"UPDATE customerdetails SET remaining_money = '{float(cusDetails[4]) - float(reduceMoney)}' WHERE contact_no = '{cusDetails[1]}'")
                    DB_OBJECT.commit()
                    print(f"\nDue Amount is successfully Reduced to '{float(cusDetails[4]) - float(reduceMoney)}'")
                    go_back_to_customer_view()
            else:
                print("\nError: Invalid Input")
                reduce_from_due_amount()
    else:
        print("\nError: Invalid Input")
        reduce_from_due_amount()

def most_visited_cus_sorting():
    """ Function to find the most visited customer """
    
    latestBillID = get_latest_bill_id()
    if latestBillID == 0:
        print("\nError: No Bills Are Added Yet...")
        go_back_to_bill_view() 
    else:
        DB_CURSOR.execute("SELECT cus_id,COUNT(cus_id) AS 'count' FROM billdateandcustomertracker GROUP BY cus_id ORDER BY count DESC LIMIT 5")
        result = DB_CURSOR.fetchall()
        
        x_axis = []
        y_axis = []
        for cusId, count in result:
            x_axis.append(f"{get_customer_details_from_cus_id(int(cusId), 1)[2]}({cusId})")
            y_axis.append(int(count))

        plot_bar_graph(
            'Most Visited Customer (Top 5)',
            'Customer Name (ID)',
            'No. of Times Visited',
            x_axis,
            y_axis
        )

def plot_bar_graph(
    graphTitle,
    xAxisLable,
    yAxisLable,
    xAxisData,
    yAxisData
):
    """ plotting the graph based on most visited customer, using `matplotlib` """

    print('\nPlotting..')
    colors = ['#3771EF','#DAB839','#DD602F','#CE2FDD','#2FDD8F']
    plt.title(graphTitle, size='15', color='blue')
    plt.xlabel(xAxisLable, color='green', size='12')
    plt.ylabel(yAxisLable, color='green', size='12')
    plt.bar(xAxisData, yAxisData, color=colors)
    plt.grid()

    print("\nApplication won't respond until you close the graph..")
    plt.show()

    go_back_to_graph_page()

def graph_page():
    """ Serves as a Graph page """

    print("\n---Graph Page---\n\n1. Price Details.\n2. Most Sold Products (Top 5)\n3. Most Visited Customer (Top 5)\n4. Go Back to Home Page.")
    option = input('\nEnter a Valid Option : ')

    if option == '1':
        price_details_interface()
    elif option == '2':
        most_sold_product_sorting()
    elif option == '3':
        most_visited_cus_sorting()
    elif option == '4':
        home_page()
    else:
        print('\nError: Invalid Option')
        bill_view_page()

def customer_view_page():
    """ Serves as a Customer View Page """

    print("\n---Customer View Page---\n\n1. Search for a Customer Using Name.\n2. Search for a Customer Using Contact Number.\n3. Reduce from the Due Amount.\n4. Go Back to Home Page.")
    option = input('\nEnter a Valid Option : ')

    if option == '1':
        search_customer_using_name()
    elif option == '2':
        search_customer_using_con_no()
    elif option == '3':
        reduce_from_due_amount()
    elif option == '4':
        home_page()
    else:
        print('\nError: Invalid Option')
        customer_view_page()

def home_page():
    """ Serves as a Home Page. """

    print("\n---Home Page---\n\n1. Enter bill.\n2. Add Products.\n3. Add Stocks\n4. Remove Products.\n5. Edit the Price of a Products.\n6. Show older bills.\n7. View Customer Details.\n8. Show all the product details (in terminal).\n9. Show all the product details (in csv).\n10. Show all the backup product details (in terminal).\n11. Show all the backup product details (in csv).\n12. Show Stock Alerts\n13. Plot Graphs.\n14. Exit.")
    option = input('\nEnter a Valid Option : ')

    if option == '1':
        enter_cus_details()
    elif option == '2':
        enter_product_details()
    elif option == '3':
        add_stock_interface()
    elif option == '4':
        check_limit_remove()
    elif option == '5':
        edit_product_price()
    elif option == '6':
        bill_view_page()
    elif option == '7':
        customer_view_page()
    elif option == '8':
        show_product_details_in_terminal()
    elif option == '9':
        show_product_details_in_csv()
    elif option == '10':
        show_backup_product_details_in_terminal()
    elif option == '11':
        show_backup_product_details_in_csv()
    elif option == '12':
        show_stock_alert()
    elif option == '13':
        graph_page()
    elif option == '14':
        DB_OBJECT.close()
        print('\nExiting..')
    else:
        print('\nError: Invalid Option')
        home_page()

username_input = input('\nUsername (MySQL localhost) : ')
password_input = input('\nPassword (MySQL localhost) : ')
log_in(username_input, password_input)
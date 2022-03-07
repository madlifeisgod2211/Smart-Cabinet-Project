
import gspread
import pyrebase
import time
import schedule
import mysql.connector
import RPi.GPIO as GPIO
from pynput.keyboard import Key, Controller
from datetime import date, datetime
from threading import Timer
from oauth2client.service_account import ServiceAccountCredentials
from time import sleep
from mfrc522 import SimpleMFRC522
from config import firebaseConfig

#Create empty list
Id_list = []
id_list = []
Status_list = []
State_1 = 1
State_2 = 0
firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()
red_led = 11
locker = 13
button = 15
buzzer = 16


#VARIABLES AND CALLBACK FUNCTION

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(locker,GPIO.OUT)
GPIO.setup(red_led, GPIO.OUT)
GPIO.setup(buzzer,GPIO.OUT)
GPIO.setup(button, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.output(locker,GPIO.LOW)
GPIO.output(red_led, GPIO.HIGH)
GPIO.output(buzzer, GPIO.HIGH)
reader = SimpleMFRC522()
GPIO.setwarnings(False)
gc = gspread.service_account(filename = "users.json")
gsheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1_FranxE4OZcJEI9B8jVgt_KATEsnzwS8jy7mJkEnrqc/edit#gid=0")
wsheet = gsheet.worksheet("Sheet 1")
rows = len(wsheet.get())
isClosed = True


def write():
    text = input("Please enter new user's name: ")
    print("Please place the card to complete writing")
    id, name = reader.write(text)
    print("Data" + name + " writing is completed")
    
def read():
    print("Reading ... Please place the card ... ")
    id, text = reader.read()
    print("ID: %s \n Text: %s" % (id,text))
    return id
        

def update(pos,value):
    wsheet.update(pos, value)
    print("Data is updated")
    
def new(data):
    rows = len(wsheet.get())
    wsheet.insert_row(data,rows + 1)
    print("New data is inserted")
    
def get_id():
    print("Get all ID")
    return wsheet.col_values(1)

def destroy():
    GPIO.cleanup()

# ------------------------------- RFID DESKTOP -------------------------
def update_data(tagId, Status_list):
   db.child("ID").child(tagId).update({"Status":Status_list})
    
def Update_RFID(Status_list, Id_list):
    Caplocks()
    for i in range(0,len(Id_list)):
        update_data(Id_list[i], Status_list[i])
    print("Update sucessfully")
    time.sleep(1)
    count = 0
    for k in range(0, len(Id_list)):
        if Status_list[k] == State_1:
            count += 1
        else:
            count += 0
    print("Total id: " + str(count))
    if count >= 3:
         print("Turn on the green LED")
         #GPIO.output(red_led,1)
    else:
         print("Turn on the red LED")
         GPIO.output(red_led,GPIO.LOW)
    
    for j in range(0,len(Id_list)):
        Status_list[j] = State_2
    print(Status_list)
    Caplocks()

def check_license():
    key = db.child("License").child("Key").get()
    return key.val()

data = db.child("ID").shallow().get()
Id_list = list(data.val())
id_list = get_id()

def import_data():
    for i in data.val():
        Status = db.child("ID").child(i).child("Status").get()
        #Status_list.append(Status.val())
        Status_list.append(0)
    
def Caplocks():
    keyboard = Controller()
    keyboard.press(Key.caps_lock)
    keyboard.release(Key.caps_lock)

def Activate():
    keyboard = Controller()
    keyboard.press(Key.caps_lock)
    keyboard.release(Key.caps_lock)
    keyboard.press(Key.caps_lock)
    keyboard.release(Key.caps_lock)

def Pass():
    enter = Controller()
    enter.press('2')
    enter.press('2')
    enter.press('7')
    enter.press('1')
    enter.press('9')
    enter.press(Key.enter)
    enter.release(Key.enter)
    

def RFID_Reader(Status_list, Id_list):
    #Start to read ID tag
    set_timer = 4
    t = Timer(set_timer, Pass)
    t.start()
    tagId_untransformed = input("Enter the RFID tag: ")
    t.cancel()
    tagID = tagId_untransformed.split('227')[1]
    print("RFID Tag is: " + str(tagID))
    
    #Compare ID tag to ID list
    for i in range (0,len(Id_list)):
        if tagID == Id_list[i]:
            Status_list[i] = State_1
        elif Status_list[i] != State_2:
            Status_list[i] = State_1
        else:
            Status_list[i] = State_2
def button_close():
    if GPIO.input(button) != GPIO.HIGH:
        GPIO.output(locker, GPIO.LOW)
        GPIO.output(red_led, GPIO.LOW)
        time.sleep(0.5)
        GPIO.output(red_led, GPIO.HIGH)
        print("CLOSE THE DOOR")
        return True
    else:
        return False


def openDoor():
    GPIO.output(locker, GPIO.HIGH)
    GPIO.output(buzzer, GPIO.LOW)
    time.sleep(0.5)
    GPIO.output(buzzer, GPIO.HIGH)
    print("OPEN THE DOOR")

def closeDoor():
    GPIO.output(locker, GPIO.LOW)
    GPIO.output(red_led, GPIO.LOW)
    time.sleep(0.5)
    GPIO.output(red_led, GPIO.HIGH)

def door(isClosed):
    while isClosed:
        id = read()
        id = str(id)
        for i in range(1, rows):
            if id == id_list[i]:
                isClosed = False
                break
    if isClosed == False:
        openDoor()
    elif isClosed == True or button_close() == True:
        closeDoor()
    return isClosed

def main(isClosed):
    license_key = 2021
    Caplocks()
    if check_license() == license_key:
        print("Your key is valid")
        #import_data()
        schedule.every(1).seconds.do(RFID_Reader, Status_list, Id_list)
        schedule.every(10).seconds.do(Update_RFID, Status_list, Id_list)
        
        while True:
            run = button_close()
            if isClosed == False and run != True:
                print("Check button")
                schedule.run_pending()
                time.sleep(1)
            else:
                break
    
    else:
        while True:
            print("Error ... Your system has been disabled")
            GPIO.output(red_led, GPIO.LOW)
            time.sleep(2)
            GPIO.output(red_led, GPIO.HIGH)
            



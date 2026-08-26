# -*- coding: utf-8 -*-
'''
Created on 25.08.2023

@author: Administrator
'''
import threading
import time


log_array = []
log_array.append('[Console Logs]')
log_array.append('<---------------------------------------->')
log_array.append(' ')


def add_log(type, thread, message):
    if thread == "Main":
        log_array.append(
            time.strftime("%H:%M:%S", time.localtime()) + " | Thread " + thread + " [" + type + "] - " + message)
    else:
        log_array.append(time.strftime("%H:%M:%S",
                                              time.localtime()) + " | Thread " + f"{thread}" + " [" + type + "] - " + message)

def print_new_messages():
    last_printed_index = -1  # Start with -1 to indicate no messages have been printed
    while True:
        if len(log_array) > last_printed_index + 1:  # Check if there are new messages
            # Print all new messages
            for i in range(last_printed_index + 1, len(log_array)):
                print(log_array[i])
                last_printed_index = i  # Update the last printed index
        time.sleep(1)  # Sleep for a while to avoid busy waiting

# Example usage
# Start the thread that prints new messages
threading.Thread(target=print_new_messages).start()

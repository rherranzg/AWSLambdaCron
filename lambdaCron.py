from datetime import datetime
from urllib2 import urlopen
import boto3
import re

REGION = "eu-west-1"
t = datetime.now()

def match(unit, range):
    '''
    Main function to compare the current time with the time defined in cron expression
    The main purpose of this funcion is validate types and formats, and decide if 'unit' match with 'range'
    
    "Unit" must be an integer with the current time
    "Range" must be a string with the value or values defined in cron expression
    '''
    
    # Validate types
    if type(range) is not str or type(unit) is not int:
        return False
    
    # For wildcards, accept all
    if range == "*":
        return True
    
    # Range parameter must match with some valid cron expression (number, range or enumeration) -> "*", "0", "1-3", "1,3,5,7", etc
    pattern = re.compile("^[0-9]+-[0-9]+$|^[0-9]+(,[0-9]+)*$")
    if not pattern.match(range):
        print "There is an error in the cron line"
        return False
    
    # If range's length = 1, must be the exact unit number
    if 1 <= len(range) <= 2:
        if unit == int(range):
            return True
    
    # For ranges, the unit must be among range numbers
    if "-" in range:
        units = range.split("-")
        if int(units[0]) <= unit <= int(units[1]):
            return True
        else:
            return False
    
    # For enumerations, the unit must be one of the elements in the enumeration
    if "," in range:
        if str(unit) in range:
            return True
    
    return False

def checkMinutes(cronString):
    
    return match(t.minute, cronString.split()[0])
    '''if match(t.minute, cronString.split()[0]):
        print ">> Mins OK"
        return True
    else:
        print ">> Mins NOT OK"
        return False'''


def checkHours(cronString):
    
    return match(t.hour, cronString.split()[1])
    '''if match(t.hour, cronString.split()[1]):
        print ">> Hour OK"
        return True
    else:
        return False'''


def checkDays(cronString):
    
    return match(t.day, cronString.split()[2])
    '''if match(t.day, cronString.split()[2]):
        print ">> Day OK"
        return True
    else:
        return False'''

def checkMonths(cronString):

    return match(t.month, cronString.split()[3])
    '''if match(t.month, cronString.split()[3]):
        print ">> Month OK"
        return True
    else:
        return False'''

def checkWeekdays(cronString):

    return match(t.isoweekday(), cronString.split()[4])
    '''if match(t.isoweekday(), cronString.split()[4]):
        print ">> Weekday OK"
        return True
    else:
        return False'''
        
def isTime(cronString):
    '''
    This function returns True if this precise moment match with the cron expression.
    This functions can be as smart as you need. Right now, it only match the present hour
    with the hour defined in the cron expression.
    '''
    
    if checkMinutes(cronString) and checkHours(cronString) and checkDays(cronString) and checkMonths(cronString) and checkWeekdays(cronString):
        return True
    
def cronExec(cron, instance, action):
    
    print "> {2}. La fecha actual es {0} y el cron es {1}".format(t, cron, action)
    
    if isTime(cron):
        if action == "start" and instance.state["Name"] == "stopped":
            # Start Instance
            print "#################################"
            print "## Starting instance {0}...".format(instance.id)
            print "#################################"
            instance.start()
            
        if action == "stop" and instance.state["Name"] == "running":
            # Stop instance
            print "#################################"
            print "## Stopping instance {0}...".format(instance.id)
            print "#################################"
            instance.stop()
    
def checkEC2(ec2):
    '''List and print tags in EC2 running instances
    '''
    
    for i in ec2.instances.all():
        print "> Instance {0} is {1}".format(i.id, i.state["Name"])
        for tag in i.tags:
            if tag['Key'] == "startTime":
                #print ">> Found an 'startTime' tag..."
                cronExec(tag['Value'], i, "start")
                
            if  tag['Key'] == "stopTime":
                #print ">> Found an 'stopTime' tag..."
                cronExec(tag['Value'], i, "stop")
                
    return 1

def lambda_handler(event, context):
    
    # start connectivity
    s = boto3.Session()
    ec2 = s.resource('ec2')
    #rds = s.resource('rds')
    
    try:
        if checkEC2(ec2):
            return "Success!"

        #if checkRDS(rds):
        #   return "Success!"

    except:
        print('Check failed!')
        raise
    finally:
        print('Check complete at {}'.format(str(datetime.now())))
from datetime import datetime, date
from urllib2 import urlopen
import boto3
import re

t = datetime.now()
DEBUG = True

ec2_client = boto3.client('ec2')

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
        #print "There is an error in the cron line"
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

def checkHours(cronString):
    
    return match(t.hour, cronString.split()[1])

def checkDays(cronString):
    
    return match(t.day, cronString.split()[2])

def checkMonths(cronString):

    return match(t.month, cronString.split()[3])

def checkWeekdays(cronString):

    return match(t.isoweekday(), cronString.split()[4])
        
def isTime(cronString):
    '''
    This function returns True if this precise moment match with the cron expression.
    This functions can be as smart as you need. Right now, it only match the present hour
    with the hour defined in the cron expression.
    '''
    
    if checkMinutes(cronString) and checkHours(cronString) and checkDays(cronString) and checkMonths(cronString) and checkWeekdays(cronString):
        return True
    
def cronEC2Exec(cron, instance, action):
    '''
    Function to control operations on EC2 instances
    '''
    if DEBUG:   print "> {2}. Current date is {0} and cron expression is {1}".format(t, cron, action)
    if cron == "":
        print "Empty cron expression!"
        return True
    
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
            
        if action == "createAmi":
            # Create AMI
            print "#################################"
            print "## Creating AMI for instance {0}...".format(instance.id)
            print "#################################"
            response = ec2_client.create_image( DryRun=False, InstanceId=instance.id, Name='ami-{0}-{1}'.format(instance.id, date.today()), Description='AMI backup for instance {0}'.format(instance.id), NoReboot=True)

def cronAMIExec(cron, ami, action):
    '''
    Function to control operations on AMIs
    '''
    if DEBUG:   print "[cronAMIExec] > {2}. Current date is {0} and cron expression is {1}".format(t, cron, action)
    if cron == "":
        print "Empty cron expression!"
        return True
    
    if isTime(cron):

        if action == "delete" and ami is not None:
            # Delete AMI
            print "#################################"
            print "## Deleting AMI {0}...".format(ami)
            print "#################################"
            response = ec2_client.deregister_image( DryRun=False, ImageId=ami )

def cronEBSExec(cron, ebs, action):
    '''
    Function to control operations on EBSs
    '''
    if DEBUG:   print "[cronEBSExec] > {2}. Current date is {0} and cron expression is {1}".format(t, cron, action)
    if cron == "":
        print "Empty cron expression!"
        return True
        
    if isTime(cron):
        if action == "createSnapshot":
            # Create Snapshot
            print "#################################"
            print "## Creating Snapshot {0}...".format(ebs)
            print "#################################"
            ebs.create_snapshot(
                Description = "Snapshot created by LambdaCron at {0}-{1}-{2} {3}h {4}' {5}''".format(t.year, t.month, t.day, t.hour, t.minute, t.second)
                )

def cronSnapExec(cron, snap, action):
    '''
    Function to control operations on Snapshots
    '''
    if DEBUG:   print "[cronSnapExec] > {2}. Current date is {0} and cron expression is {1}".format(t, cron, action)
    if cron == "":
        print "Empty cron expression!"
        return True
    
    if isTime(cron):

        if action == "delete" and snap is not None:
            # Delete Snapshot
            print "#################################"
            print "## Deleting Snap {0}...".format(snap)
            print "#################################"
            response = ec2_client.delete_snapshot( DryRun=False, SnapshotId=snap )

def checkEC2(ec2):
    '''
    List tags in EC2 instances and perform operations on instances
    '''
    
    for i in ec2.instances.all():
        #print "> Instance {0} is {1}".format(i.id, i.state["Name"])
        if i.tags:
            for tag in i.tags:
                if tag['Key'] == "startInstance":
                    if DEBUG:   print ">> Found an 'startInstance' tag on instance {}...".format(i.id)
                    cronEC2Exec(tag['Value'], i, "start")
            
                if tag['Key'] == "stopInstance":
                    if DEBUG:   print ">> Found an 'stopInstance' tag on instance {}...".format(i.id)
                    cronEC2Exec(tag['Value'], i, "stop")
                    
                if tag['Key'] == "createAmi":
                    if DEBUG:   print ">> Found an 'createAmi' tag on instance {}...".format(i.id)
                    cronEC2Exec(tag['Value'], i, "createAmi")

    return True

def checkAMIs():
    '''
    Function which lists images, for example, to perform deletions
    '''
    
    amis = ec2_client.describe_images(Filters=[ { 'Name': 'tag-key', 'Values': [ "deleteAmi" ] } ])
    if amis is not None:
        for ami in amis["Images"]:
            if DEBUG:   print "[checkAMIs] La AMI {0} tiene los tags {1}".format(ami["ImageId"], ami["Tags"])

            for tag in ami["Tags"]:
                if tag['Key'] == "deleteAmi":
                    cronAMIExec(tag['Value'], ami["ImageId"], "delete")

    return True

def checkEBS(ec2):
    '''
    List tags in EBS Volumes and perform operations on them
    '''
    
    for ebs in ec2.volumes.all():
        if DEBUG:   print "Volumen {0} con tags {1}".format(ebs.id, ebs.tags)

        if ebs.tags:
            for tag in ebs.tags:
                if tag['Key'] == "createSnapshot":
                    if DEBUG:   print ">> Found a 'createSnapshot' tag with value {}".format(tag['Value'])
                    cronEBSExec(tag['Value'], ebs, "createSnapshot")

    return True

def checkSnapshots():
    '''
    Function which lists snapshots, for example, to perform deletions
    '''
    
    snaps = ec2_client.describe_snapshots(Filters=[ { 'Name': 'tag-key', 'Values': [ "deleteSnapshot" ] } ])
    if snaps is not None:
        for snap in snaps["Snapshots"]:
            if DEBUG:   print "[checkSnapshots] El snap {0} tiene los tags {1}".format(snap["SnapshotId"], snap["Tags"])

            for tag in snap["Tags"]:
                if tag['Key'] == "deleteSnapshot":
                    cronSnapExec(tag['Value'], snap["SnapshotId"], "delete")

    return True

def lambda_handler(event, context):
    
    # start connectivity
    s = boto3.Session()
    ec2 = s.resource('ec2')
    
    try:
        if checkEC2(ec2):
            print "EC2 checked!"
        if checkAMIs():
            print "AMIs checked!"
        if checkEBS(ec2):
            print "Volumes checked!"
        if checkSnapshots():
            print "Snaps checked!"

    except Exception as e:
        print('Check failed!')
        print str(e)
        raise
    finally:
        print('Check complete at {}'.format(str(datetime.now())))
        return "OK"

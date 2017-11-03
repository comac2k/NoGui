#!/usr/bin/python
import glob
import random
import select
import os
import subprocess
import re
import signal
import threading
import sys
import time
import logging
import shutil
import distutils.dir_util


logging.basicConfig(filename='/home/pi/RetroPie/roms/rungames.log',level=logging.ERROR)

INACTIVITY_TIMEOUT = 150
HIGH_VOLUME_TIMEOUT = 60

VOLUME_LOW = 25 
VOLUME_HIGH = 115

isVolumeHigh = True

game_exclusions = [ '.*/neogeo/neogeo.zip', '.*/doesntwork/.*' ]


def setVolumeLow() :
	global isVolumeHigh
	if isVolumeHigh :
		isVolumeHigh = False
		setVolume(VOLUME_LOW)

def setVolumeHigh() :
	global isVolumeHigh
	if not isVolumeHigh :
		isVolumeHigh = True
		setVolume(VOLUME_HIGH)

def setVolume(vol) :
	os.popen('amixer sset Speaker ' + str(vol) )

def getVolume() :
	vol = os.popen('amixer sget Speaker | grep "Left: Playback" | sed -e \'s/.*Playback \([^ ]*\).*/\\1/g\'').read()
	return int(vol)


def filter_games(gamename) :
	for rule in game_exclusions:
		if re.match(rule, gamename) != None : return False
	return True


gamelist = filter(filter_games, glob.glob('/home/pi/RetroPie/roms/*/*.zip'))

def getRandomGame() :
	global gamelist
	random.shuffle(gamelist)
	logging.info('Random game selected: ' + gamelist[0])
	return gamelist[0]


def blacklist_game(gamename) :
	global gamelist
	gamelist.remove(gamename)
	filename = os.path.basename(gamename)
	filepath = os.path.dirname(gamename)
	newpath = filepath + '/doesntwork'
	distutils.dir_util.mkpath(newpath)
	shutil.move(gamename, newpath + '/' + filename)


def inputAvailable(fds, timeout, exitPipeFd) :
	global current_game
	#logging.info('Checking for input on: ' + str(fds) + ', exitFd= '+str(exitPipeFd))
	(rd, wr, sp) = select.select(fds, [], [], timeout)
	#logging.debug('Select reported read available on: ' + str(rd))
	result = rd != []
	while (rd != []):
		rd[0].read(1)
		if rd[0] == exitPipeFd:
			logging.warning('Dead child received in main loop (inputAvailable)')
			result = False
			blacklist_game(current_game)
		(rd, wr, sp) = select.select(fds, [], [], 0)
	#logging.info('inputAvailable = ' + str(result))
	return result

fds = map( lambda fn : open(fn, 'r'), glob.glob('/dev/input/event*') )

def killprocs(pid):
	try:
		os.kill(pid, signal.SIGTERM)
	except:
		pass


def killgame(pid):
	subp = subprocess.Popen('pstree '+str(pid)+' -p -a -l | cut -d, -f2 | cut -d\' \' -f1', stdout=subprocess.PIPE, shell=True)
	result = subp.communicate()[0].split('\n')
	map(lambda procid : killprocs(int(procid)), filter(lambda v : v != '', result))

proc = 0

def popenAndCall(onExit, *popenArgs, **popenKWArgs):
    """
    Runs a subprocess.Popen, and then calls the function onExit when the
    subprocess completes.

    Use it exactly the way you'd normally use subprocess.Popen, except include a
    callable to execute as the first argument. onExit is a callable object, and
    *popenArgs and **popenKWArgs are simply passed up to subprocess.Popen.
    """

    def runInThread(onExit, popenArgs, popenKWArgs):
        global proc
        proc = subprocess.Popen(*popenArgs, **popenKWArgs)
        onExit(proc.wait())
        return

    thread = threading.Thread(target=runInThread,
                              args=(onExit, popenArgs, popenKWArgs))
    thread.start()

    return thread


def on_exit(code):
	global game_start_time
	global exitPipeWrite
	logging.info('onExit received at '+str(time.time()))
	if (code == 0):
		if (time.time() - game_start_time > 10):
			logging.info('Game exited by user after 10sec. Exiting.')
			setVolume(initialVolume)
			os._exit(0)
		else:
			logging.info('Game exited before 10sec. Assumed dead. Signaling to main thread')
			exitPipeWrite.write('a')
			logging.info('Signaled')
	else:
		logging.info('Game exited with nonzero result. Assumed dead. Signaling to main thread')
		exitPipeWrite.write('b')
		logging.info('Signaled')


def purgueFd(fd) :
	(rd, wr, sp) = select.select([fd], [], [], 0)
        result = rd != []
        while (rd != []):
                rd[0].read(1)
                (rd, wr, sp) = select.select([fd], [], [], 0)


def clearScreen() :
	os.system('clear')


exitPipeRead, exitPipeWrite = os.pipe()
exitPipeRead, exitPipeWrite = os.fdopen(exitPipeRead,'r',0), os.fdopen(exitPipeWrite,'w',0)
fds.append(exitPipeRead)

logging.info('exitPipeRead: ' + str(exitPipeRead))

os.system('alias dialog=:')

initialVolume = getVolume()
setVolumeLow()

while 1 :
	purgueFd(exitPipeRead)
	clearScreen()
	gamefile = getRandomGame()
	current_game = gamefile
	emulator = re.search('.*/([^/]+)/[^/]+', gamefile).group(1)
	cmd = '/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ "' + emulator + '" "'+gamefile+'"'
	game_start_time = time.time()
	logging.info('Starting game at '+str(game_start_time)+': '+cmd)
	popenAndCall(on_exit, cmd, stdin=0, stdout=1, stderr=2, shell=True)#, preexec_fn=os.setsid)

	timeOutTime = INACTIVITY_TIMEOUT
	while (inputAvailable(fds, timeOutTime, exitPipeRead)):
		setVolumeHigh()
		while (inputAvailable(fds, HIGH_VOLUME_TIMEOUT, exitPipeRead)):
			pass
		setVolumeLow()
		timeOutTime = INACTIVITY_TIMEOUT - HIGH_VOLUME_TIMEOUT
		pass

	setVolumeLow()
	logging.info('Killing game at '+str(time.time()))
	killgame(proc.pid)
	time.sleep(1)


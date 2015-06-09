=== ASSIGNMENT INFORMATION ===
Name: 		Peter Gordon
Email:		peter.gordon@csu.fullerton.edu
Course:		CPSC 471, T/Th 11:30-12:45
Instructor:	Dr. M. Gofman
Assignment:	3 (FTP Server/Client)
Due:		2014-05-20, Midnight
Language:	Python 3


=== STATUS ===
The client/server reference implementations are complete, including relevant
error checking and handling.


=== HOW TO USE ===
(In these examples, the beginning "$" is a command prompt.)
The forking server can be run with:
	$ python3 ./forkserv.py <port>

The threading server can be run with:
	$ python3 ./threadserv.py <port>

The client can be run with:
	$ python3 ./cli.py <host> <port>
	
Alternatively, if the scripts are executable, they can be called directly
(that is, eliminating the need to include the "python3" in each of the above
examples).

=== FILES INCLUDED ===
In addition to this README, the following source code is included with this
submission:
	(1 ) ClientConnection.py -- The ClientConnectionInterpreter abstract base
			class;
	(2 ) cli.py -- The executable client script;
	(3 ) forkserv.py -- The executable forking server script;
	(4 ) libserver.py -- Implementations of the forking/threading server code;
	(5 ) ServerConnection.py -- The ServerConnectionHandler abstract base
			class;
	(6 ) SimpleFTPClientInterpreter.py -- The SimpleFTPClientInterpreter
			implementation, used for the client command interpreter;
	(7 ) SimpleFTPServerConnection.py -- The SimpleFTPServerConnectionHandler
			implementation, used for processing commands on the server;
	(8 ) threadserv.py -- The executable threading server script;
	(9 ) timer.py -- The Timer class, a simple timer as a context manager; and
	(10) utils.py -- A module containing miscellaneous utility functions and
		structures used throughout the project.

The original problem statement and assignment description is also included 
	
=== SERVER DESIGN ===
The server has both forked (forkserv.py) and threaded (threadserv.py)
implementations. Both listen on the target port until they are stopped by a
keyboard interrupt (such as Ctrl+C on Linux/Unix systems) or otherwise killed
by the operating system. These server loops will fork a new child process or
spawn a new thread, respectively, to handle each new client connection.

The listening code and the protocol are separated logically such that the
server could be used for other protocols by subclassing the abstract
ServerConnectionHandler type and implementing its handleClientConnection
method (at least), then passing that new type name as the second parameter to
the appropriate listenForever function. For each client connection, the server
creates an instance of that class with the client's IP address and port, and
then calls its handleClientConnection method in the created child thread or
process. 

In addition to this, the mechanism for interpreting protocol commands is also
abstracted. The SimpleFTPServerConnectionHandler class, which is the core of
this protocol's reference server implementation, has a method for handling
each protocol command. These are then mapped, via calls to its
registerProtocolHandler method, to regular expressions holding the syntax for
that command. This allows the protocol to be easily extended by simply adding
methods and their associated regular expressions to handle new commands.
Moreover, this use of regular expressions makes validation and extraction of
data much less complex. 

This abstraction was not required in the problem statement; but
to this author, is a very good practice. 


=== CLIENT DESIGN ===
The client is also abstracted, and provides at its core a simple interpreter
which is layered similar to the server code. The client could be used for
other command-centric protocols by subclassing ClientConnectionInterpreter
and implementing its handleCommand and clientFinished methods (at least).

The SimpleFTPClientInterpreter class, which is the core of this protocol's
reference client implementation, implements the commands in a manner similar
to the server's use of callbacks. It has a method for handling each user
command, which are then mapped, via calls to registerCommandHandler, to
regular expressions holding the syntax of the command. Similarly, this allows
the protocol to be easily extended, and commands to be easily verified/parsed.
Lastly, using these callback methods from one central handler
(handleCommand) allows for easier maintenance of the data channel, as its
setup/teardown is logically separated from the command handler callbacks, so
they can be guaranteed a data connection exists (if necessary). 

Again, this abstraction was not required by the problem statement; but is a
good practice in this author's opinion.


=== PROTOCOL DESIGN ===
The protocol used in my server-client architecture is similar in concept to
the File Transfer Protocol established in RFC 959. The protocol uses two TCP
connections: a control channel and a data channel.

After the initial TCP connection is established (control), the client can
then send one of the following commands, explained below. 

Each command is terminated by a newline. For any transfers, an ephemeral
connection will be established through which data for the command will be
sent. The commands used have the following syntax:

(1) GET
	Syntax: 		GET <filename>
	Ctrl response:	OK <size>
	Ctrl response:	ERR <message>
	Data response: 	<file contents>
	
	GET is used to retrieve a file from the server. After opening a data
	connection, the client issues sends the command "GET <filename>" and the
	server responds on the control channel with the status. <status> can be one
	of "OK" or "ERR". "OK" is sent when the file exists and is ready to be
	transmitted, and a "ERR" is sent if the file cannot be transmitted.
	The <code> transmitted for an "OK" message is the file size; or an error
	string for a "ERR" message, which gives specific information on why the
	file could not be transmitted.

	
(2) PUT
	Syntax:			PUT <size> <filename>
	Ctrl response:	READY <size>
	Ctrl response:	OK <size>
	Ctrl response:	ERR <message>
	Data response:	(None)
	
	PUT is used to upload a file to the server. After opening a data
	connection, the client issues the command "PUT <size> <filename>" where
	<filename> and <size> are the name and size (bytes) of the file to be
	uploaded, respectively. The server will respond "READY <size>" if it is
	ready to receive the file on the data connection; or "ERR" if it cannot
	store the file, with a message giving the reason. After the READY reply,
	file data is then read as the next <size> bytes from the data channel.
	Upon succesful receipt of the file contents, the server will respond with
	"OK <size>", where <size> is the number of bytes written to the file on
	the server. If the file was not uploaded and written successfully, an
	error reply ("ERR <reason>") is given on the control channel.

	
(3) LS
	Syntax:			LS
	Ctrl response:	OK <size>
	Ctrl response:	ERR <message>
	Data response:	<size> <filename> (one line for each file/directory)
	
	LS is used to list the contents of the remote (server) directory. After
	opening a data connection, the client sends the command "LS". The server
	then responds with "ERR" and a brief error code if it could not create the
	list, or "OK <size>" where <size> is the length of the output list (in
	bytes) (including newlines between the files.) The output format is a
	series of lines, one for each file or directory, where the first field
	is the size in bytes (or "DIR" if the entry is a directory), and the second
	is the name of that entry.

	
(4) DATA
	Syntax:			DATA
	Syntax:			DATA <port#>
	Ctrl response:	READY <port#> (Passive only)
	Ctrl response:	OK <port#>
	Ctrl response:	ERR <message>
	Data response:	(None)
	
	The DATA command is used to establish the data channel for transferring
	file/list data from one of the GET/PUT/LS commands. There are two methods
	to establish this connection: passive or not passive.
	
	In the default mode (not passive), the client listens for data connections
	on an ephemeral port, then sends the command "DATA <port>", where <port>
	is that ephemeral port number. The server then connects to the client at
	that port, upon which the client responds to the server "OK <port>" to
	acknowledge the connection.
	
	However, this can be problematic when the client is behind a NAT setup or
	firewalls that prohibit incoming connections. For this reason, passive mode
	can be enabled. In passive mode, when the client wishes to create a data
	channel, it sends the DATA command on the control channel. The server then
	starts listening for incoming connections on an ephemeral port, and
	responds on the control channel with "READY <port>". After the client
	connects, the server responds on the control channel with "OK <port>" to
	acknowledge the connection. (If there was an error through any of this, it
	instead responds with "ERR <message>" giving a brief reason.)
	
	The client (for GET and LS requests) and server (for PUT requests) are
	responsible for closing this connection after the relevant transfer
	is completed.


(5) GO AWAY
	Syntax:			GO AWAY
	Ctrl response:	OK BYE
	Data response:	(None)
	
	This command instructs the server to close the control channel and stop
	processing any further commands. In addition, the data connection, if
	open, will be closed. ("Do you wanna build a protocol?" ...)

In addition to these five required components, I also implemented additional
protocol messages to configure and modify some transfer behavior on-the-fly.
These are as follows.

(6) SETCONFIG
	Syntax:			SETCONFIG <option> <value>
	Ctrl response:	OK <option> <new value>
	Data response:	(None)
	
	This command is used to adjust some transfer setting variables at
	runtime. <option> is one of:

		CHUNKSIZE -- (integer, default 65536)
			The chunk size (bytes) used for reading and writing file data in
			GET/PUT requests.

		PASSIVE -- (YES/NO string, default NO)
			Whether or not to use passive mode for establishing data
			connections. See DATA details for more information.
	
		PERSISTENTDATA -- (YES/NO string, default NO)
			Whether the data connection should be persistent (that is, created
			once and used for all subsequent data transfers, instead of
			per-command). If it is changed from YES to NO and a data
			connection is already established, then that data connection will
			be closed after the next transfer which uses it (or when the
			connection is terminated via the GO AWAY command.)

		PUTBEHAVIOR -- (string, default ERROR)
			What to do when a PUT request attempts to write to a file that
			already exists. This can be one of:
			* APPEND -- Append the data to the existing file
			* ERROR -- Return an error to the client; 
			* OVERWRITE -- Forcibly overwrite the file.

		SOCKETTIMEOUT -- (integer, default 10)
			Time (seconds) to wait for socket connections when requesting a
			data channel.

	The server will acknowledge the change of a setting by replying
	"OK <option> <value>". For YES/NO options, the reply will instead use the
	terms "ENABLED" or "DISABLED".


(7) GETCONFIG
	Syntax:			GETCONFIG
	Ctrl response:	OK <lines>
	Ctrl response:	<option> <value>
	Data response:	(None)
	
	This command retrieves a brief listing of all user-modifiable transfer
	settings (essentially, everything that can be changed with the SETCONFIG
	command). The first line in the response is "OK <lines>", where <lines>
	is the number of lines in the reply body. Each subsequent line is then
	an option name followed by its current value, separated by a space. 


=== OTHER IMPLEMENTATION NOTES/POTENTIAL PITFALLS ===
Due to time constraints in its development, the included reference client does
not use all of the extra protocol features. In particular, it does not use the
GETCONFIG command or either of the PUTBEHAVIOR or SOCKETTIMEOUT settings.

For brevity, the example usage given below does not include changing or
printing any of the settings via SETCONFIG or GETCONFIG commands,
respectively, other than enabling and disabling passive data mode (to show the
change in syntax and protocol messages exchanged for the command). Also,
only a select few example errors are shown in this example conversation; but
all error responses are of the form "ERR <message>" where <message> is a
brief reason for the error.


=== EXAMPLE CONVERSATION ===
In these examples, S>C and C>S denote messages sent from the server to the
client, and from the client to the server, respectively. Appended to these
are a "DATA" or "CTRL", denoting if that is sent over the data or control
channels, respectively.

In this example, the client retrieves a list of the files on the server,
which are:
* HelloWorld.txt -- A text file containing "Hello, World!"
* EmptyFile.dat -- An empty file.
* anotherDir -- A directory

The client then downloads HelloWorld.txt, EmptyFile.dat, and then uploads
HelloUniverse.txt, which is a file containing "Hello, Universe!". A final
listing demonstrates that the new file is on the server.

(After the client connects to the server for the control channel...)
C>S CTRL: LS
S>C CTRL: ERR NO DATA CONNECTION
C>S CTRL: DATA 65000
(Then, after the server connects to the client port 65000...)
S>C CTRL: OK 65000
C>S CTRL: LS
S>C CTRL: OK 36
S>C DATA: 0 EmptyFile.dat
S>C DATA: 13 HelloWorld.txt 
S>C DATA: DIR anotherDir
(Here, the data connection is closed.)

C>S CTRL: GET InvalidFile.dat
S>C CTRL: ERR FILE DOES NOT EXIST

C>S CTRL: GET anotherDir
S>C CTRL: ERR FILE IS A DIRECTORY

C>S CTRL: GET HelloWorld.txt
S>C CTRL: ERR NO DATA CONNECTION
C>S CTRL: SETCONFIG PASSIVE YES
S>C CTRL: OK PASSIVE ENABLED
C>S CTRL: DATA
S>C CTRL: READY 65001
(Then, after the client connects to the server port 65001...)
S>C CTRL: OK 65001
C>S CTRL: GET HelloWorld.txt
S>C CTRL: OK 13
S>C DATA: Hello, world!
(Here, the data connection is closed.)

C>S CTRL: SETCONFIG PASSIVE NO
S>C CTRL: OK PASSIVE DISABLED

C>S CTRL: DATA 65002
(Then, after the server connects to the client port 65002...)
S>C CTRL: OK 65002
C>S CTRL: GET EmptyFile.txt
S>C CTRL: OK 0
(Here, the data connection is closed.)

C>S CTRL: DATA
S>C CTRL: READY 65003
(Then, after the server connects to the client port 65003...)
S>C CTRL: OK 65003
C>S CTRL: PUT 16 HelloUniverse.txt
S>C CTRL: READY 16
C>S DATA: Hello, Universe!
(Here, the data connection is closed.)
S>C CTRL: OK 16

C>S CTRL: DATA 65004
(Then, after the server connects to the client port 65004...)
S>C CTRL: OK 65004
C>S CTRL: LS
S>C CTRL: OK 70
S>C DATA: 13 HelloWorld.txt 
S>C DATA: 16 HelloUniverse.txt
S>C DATA: 0 EmptyFile.dat
S>C DATA: DIR anotherDir
(Here, the data connection is closed.)

C>S CTRL: GO AWAY
S>C CTRL: OK BYE
(Here, the control connection is closed.)

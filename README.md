For easy access do the following:

Create a local bin folder if you havent already
-> mkdir -p ~/bin

Upload the script into this folder using git commit
-> git commit https://github.com/Beezles/quick-gromacs-script

IF THAT DOESNT WORK THEN DO THE FOLLOWING
-> nano ~/bin/gmx_auto

paste the code, 
press ctrl + O to save,
press ctrl + X to exit,

Make it executable
-> chmod +x ~/bin/gmx_auto

verify bin was properly updated
-> grep "export PATH=\"\$HOME/bin:\$PATH\"" ~/.bashrc

Add the folder to your path if you haven't already
-> export PATH="$HOME/bin:$PATH"

You can now run the script from anywhere on your system by typing in gmx_auto

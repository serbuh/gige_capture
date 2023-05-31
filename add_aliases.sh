#!/bin/bash
echo "Enter the path to fw_cvas:"
read PATH_TO_PROJ
if [[ $PATH_TO_PROJ == "" ]];
then
  echo "Don't want to talk? So no need to bother me :?"
  exit 1
fi

echo "Sure? Hit ENTER if the path is correct"
read ACK
if [[ ! $ACK == "" ]]; then
  echo "Nothing happened"
  exit 1
fi

echo "Adding aliases to bashrc..."

echo -e '\n#CV Proj aliases\n' | tee -a ~/.bashrc
echo "alias vir=\"cd ${PATH_TO_PROJ}; source env/bin/activate\"                   # Activate virtualenv" | tee -a ~/.bashrc
echo "alias  rr=\"cd ${PATH_TO_PROJ}; python grab.py\"                            # Run" | tee -a ~/.bashrc
echo "Finished (Don't forget to run 'source ~/.bashrc')"
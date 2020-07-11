The script listens to the following commands:

!songrequest, !sr   Works as usual except the script now gathers additional
                    information about the requested video in the background.

!reloadconfig       Reloads the configuration of the script, without needing to
                    reinitialize by clicking the refresh button. You must have
                    moderator priviliges to run this command.

!db info            Gives information about the videos database in chat.

!db wipe            Wipe all video information in memory and in the videos.json
                    file.

!db load            Load the videos.json file into memory.

!db save            Save the videos in memory to the videos.json file.

If you would like to disable a certain message from being triggered. Such as the
now playing message, or one of the creative commons license warning messages,
you can simply delete the text in the field and save the settings. The message
will now be ignored and no message will be displayed in chat.

You can use the files excluded_videos.txt, excluded_channels.txt and
override_terms.txt to configure exceptions for the creative commons filter. See 
tooltips in the script settings and comments in the files themselves for more
instructions.

This script will not work without a working Youtube Data API v3 key. These keys
are free, all you will need is a Google account. You will, however, be limited
to 10.000 requests per day (so, 10.000 songs). This means you can send
approximately 7 requests per second constantly for 24 hours, without exceeding
your quota.

To create a Youtube Data API v3 key:
1. Go to https://console.developers.google.com/project
2. Click create project and enter what ever name, you can leave it on no 
   organization
3. Once it finishes creating the project, go to
   https://console.developers.google.com/ (make sure the project you just
   created is selected in the top right)
4. Click the "Enable APIs and services button"
5. Search for "youtube" and select the "YouTube Data API v3"
6. Click enable
7. In the menu on the left, click on the "Credentials" tab
8. Click the button "Create crendentials" and select "API key"
9. You now have your API key
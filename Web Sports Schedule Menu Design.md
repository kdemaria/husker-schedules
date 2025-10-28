I have created a Sports Schedules tab on the web site.

It works like this.

1. I use this [claude.ai](http://claude.ai) (sonnet 4.5) prompt to scrape the cornhusker website, and generate a package of .csv files and a summary index.html file, which is zipped up for easy downloading.  Use extended thinking for the most accurate results.

We are going to create some sports schedules in CSV format for the University of Nebraska Football, baseball, softball, mens basketball, Women's Basketball, and Volleyball.

Only consider the 2025-2026 seasons. Include all games in a season, even games in the past.  
Always refer to the teams as the "Univerisity of Nebraska Cornhuskers", "Cornhuskers", or "Nebraska Cornhuskers"

If a season has ended as of the current date, use the next season's schedule.

verify that all schedules are current as of today's date. If any games show as 'scheduled' but the date has passed, search for the actual results and update the schedule accordingly.


I suggest you use the official University of Nebraska official site https://huskers.com/sports and  espn.com to validate data, but don't limit yourself to only those sources.

Create a separate csv for each sport listed above.

Name each file in the format "Sportname.csv".

Each CSV should contain the following header: Date, Day, Opponent, Home/Away, Location, Venue, Time, Event, Result

Create an .html document that lists data in each of the CSVs as a Sports Schedule, by sport in a nicely formatted and Nebraska Branded format.


2. I download it, unzip it, and place it on a public web server. Currently a folder hidden on [https://www.demaria.net/schedule-sources/](https://www.demaria.net/schedule-sources/)   
3. In google Workspace I created a single google sheet which reads these CSVs and imports their data into a table readable by a wordpress tool [https://docs.google.com/spreadsheets/d/1di3pSc4t\_uX8LibDurD2bxbB9TzLMmwhSar3UpTaTTU/edit?usp=sharing](https://docs.google.com/spreadsheets/d/1di3pSc4t_uX8LibDurD2bxbB9TzLMmwhSar3UpTaTTU/edit?usp=sharing)  
4. In wordpress, I installed FlexTable which can read a google sheet and display it’s data real time.


# Storage


## Testing new HDDs

Test any new hard drives with `smartmon` and `badblocks`.

```
sudo smartctl -t short /dev/sdX
sudo smartctl -t long /dev/sdX
sudo badblocks -wsv /dev/sdX
```

Wait a couple of days for the last command to finish. :sob:

However you can run equivalent commands on separate disks in parallel. 

```
sudo badblocks -wsv /dev/sdX
sudo badblocks -wsv /dev/sdY
```

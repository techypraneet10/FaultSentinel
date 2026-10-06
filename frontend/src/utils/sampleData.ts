/**
 * Safe synthetic demo log sequences for Operator Dashboard testing.
 * Clearly labeled as DEMO data. Contains zero hidden evaluation or test-set labels.
 */

export const DEMO_HDFS_LOGS = [
  '081109 203518 143 INFO dfs.DataNode$DataXceiver: Receiving block blk_-1608999687919862906 src: /10.250.19.102:54106 dest: /10.250.19.102:50010',
  '081109 203519 145 INFO dfs.DataNode$DataXceiver: Receiving block blk_-1608999687919862906 src: /10.250.10.6:40524 dest: /10.250.10.6:50010',
  '081109 203519 145 INFO dfs.DataNode$PacketResponder: PacketResponder 1 for block blk_-1608999687919862906 terminating',
  '081109 203519 145 INFO dfs.DataNode$PacketResponder: Received block blk_-1608999687919862906 of size 91178 from /10.250.10.6',
  '081109 203519 147 INFO dfs.DataNode$PacketResponder: PacketResponder 2 for block blk_-1608999687919862906 terminating',
  '081109 203519 147 INFO dfs.DataNode$PacketResponder: Received block blk_-1608999687919862906 of size 91178 from /10.250.19.102',
  '081109 203519 148 WARN dfs.DataNode$DataXceiver: 10.250.11.100:50010:Got exception while serving blk_-1608999687919862906 to /10.250.10.6:40524: java.io.IOException: Block blk_-1608999687919862906 is not valid.',
];

export const DEMO_BGL_LOGS = [
  '- 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.675872 R02-M1-N0-C:J12-U11 RAS KERNEL INFO generating core.1284',
  '- 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.828659 R02-M1-N0-C:J12-U11 RAS KERNEL INFO instruction cache parity error corrected',
  '- 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.983210 R02-M1-N0-C:J12-U11 RAS KERNEL INFO idoproxy: communications failure with ciod',
];

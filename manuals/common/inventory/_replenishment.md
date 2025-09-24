## Process: Replenishment

**Replenishment** is the process of moving inventory from bulk storage locations to forward-picking locations to ensure stock is always available for order fulfillment. [cite: 330, 331] It works in two stages: **Setup** and **Execution**. 

### Setup: Defining Min-Max Thresholds

This one-time setup defines the rules for when to replenish an SKU based on minimum and maximum quantity thresholds at a picking location. 

1. **Navigate**: Go to **Inventory → Replenishment** and click **Setup**. [cite: 341, 343]
2. **Select Mapping**: Click on **"Item Min Max Mapping"**. 
3. **Download Template**: Select the **Upload** option and click **Download** to get the setup file. [cite: 347, 348]
4. **Fill Template**: In the file, enter the **SKU Number**, a **Minimum Quantity** (the trigger for replenishment), and a **Maximum Quantity** (the target level). [cite: 351, 352, 353, 354]
5. **Upload and Confirm**: Upload the completed file and submit it. A success message will confirm the setup. 
6. **Update Setup**: You can later modify these rules by using the **Update** option, where setting a status to '1' deletes the SKU from the setup. [cite: 363, 376]

### Execution: Running Replenishment

This is the physical process of moving the stock. 

* **Auto Replenishment**: This is triggered automatically when an order is received, and there is not enough stock in the active picking bin to fulfill it. The required replenishment task will automatically appear in the module. 
* **Manual Replenishment**: The warehouse team can proactively initiate this by clicking the **Run Replenishment** button, which checks for any items that have fallen below their minimum threshold. 
* **Performing the Task**: For both methods, the user clicks **Export** to get a printable list of replenishment tasks. The physical stock movement is then performed similarly to a standard item movement.
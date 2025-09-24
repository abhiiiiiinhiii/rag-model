# Third-Party Integrations

This document outlines the Standard Operating Procedures (SOPs) for integrations between the WMS and third-party platforms like Shopify.

---

## Shopify Integration SOP

The WMS has an end-to-end integration with Shopify to manage catalogue, inventory, sales orders, and returns. 

### Catalogue Setup

* **Variant Management**: Product variants (e.g., size, color) must be correctly defined in Shopify, and each variant must have a corresponding and unique SKU in the WMS. The WMS treats each product variant as a separate SKU. 
* **Images**: The WMS fetches only one product image from Shopify, which is used to describe the product. 
* **Style Code**: To ensure the WMS can fetch and display a style code, it should be configured in Shopify as a product variant named "Style Code". 

### Inventory Synchronization

* **Synced Quantity**: The WMS only posts the "GOOD QC", "Sellable", and "Available" quantity to Shopify. Stock that is damaged or kept as safety stock is not shared. 
* **Sync Frequency**: Inventory is updated from the WMS to Shopify at regular intervals. 
  * A complete inventory sync happens twice a day (midnight and noon). 
  * An update occurs upon each **Putaway** of new stock into the warehouse. 
  * An update occurs each time an item is moved between an online zone (like "Good" or "SELLABLE") and an offline zone (like "Bad" or "QUARANTINE"). 

### Sales Order Fulfillment

* **Order Sync**: New orders created on Shopify, as well as cancellations, show up immediately in the WMS. 
* **Fulfillment Status**: Once an order is dispatched from the warehouse, it will be marked as “fulfilled” in Shopify. 
* **Delivery Statuses**: Last-mile delivery statuses (like In Transit, Delivered, RTO Delivered) are also shared back to Shopify after dispatch. 

### Returns and Exchanges

* The WMS manages returns and exchanges in conjunction with an app called **Return Prime**. 
* A return or exchange request (CIR) is created on Return Prime, which then shares the request with the WMS to enable fulfillment.
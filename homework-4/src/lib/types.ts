export enum OrderStatus {
  New = "New",
  Processing = "Processing",
  InDelivery = "In Delivery",
  Sent = "Sent",
}

export interface Order {
  id: string;
  createdAt: string; // ISO 8601 timestamp
  status: OrderStatus;
  orderedItems: string[]; // array of item IDs
  customerId: string;
  deliveryAddress: string;
  deliveredAt?: string; // ISO 8601 timestamp, optional
  paid: boolean;
  paymentId?: string; // optional
}

export interface CreateOrderInput {
  orderedItems: string[];
  customerId: string;
  deliveryAddress: string;
}

export interface UpdateOrderInput {
  status?: OrderStatus;
  orderedItems?: string[];
  deliveryAddress?: string;
}

export interface UpdatePaymentInput {
  paymentId: string;
}

export interface UpdateDeliveryInput {
  deliveredAt?: string;
}

export interface ListOrdersQuery {
  status?: string;
  customerId?: string;
  paid?: string;
  limit?: string;
  offset?: string;
}

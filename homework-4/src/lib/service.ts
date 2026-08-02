import { Order, OrderStatus, UpdateOrderInput } from "./types";
import store from "./store";
import { validateCreateOrder } from "./validator";

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// BUG-3: State machine for valid order status transitions
const VALID_TRANSITIONS: Record<OrderStatus, OrderStatus[]> = {
  [OrderStatus.New]: [OrderStatus.Processing],
  [OrderStatus.Processing]: [OrderStatus.InDelivery],
  [OrderStatus.InDelivery]: [OrderStatus.Sent],
  [OrderStatus.Sent]: [], // Terminal state - no transitions allowed
};

function isValidStatusTransition(currentStatus: OrderStatus, newStatus: OrderStatus): boolean {
  return VALID_TRANSITIONS[currentStatus].includes(newStatus);
}

export class OrderService {
  static createOrder(customerId: string, orderedItems: string[], deliveryAddress: string): Order {
    const validation = validateCreateOrder({ customerId, orderedItems, deliveryAddress });
    if (!validation.valid) {
      throw new Error(JSON.stringify(validation.errors));
    }

    const order: Order = {
      id: generateId(),
      createdAt: new Date().toISOString(),
      status: OrderStatus.New,
      orderedItems,
      customerId,
      deliveryAddress,
      paid: false,
    };

    return store.create(order);
  }

  static getOrderById(id: string): Order | undefined {
    return store.getById(id);
  }

  static listOrders(filters?: { status?: string; customerId?: string; paid?: boolean; limit?: number; offset?: number }): { orders: Order[]; total: number } {
    let results = store.getAll();

    // BUG-4: Use strict equality for status filter (consistent with other filters)
    if (filters?.status) {
      results = results.filter((order) => order.status === filters.status);
    }

    if (filters?.customerId) {
      results = results.filter((order) => order.customerId === filters.customerId);
    }

    if (filters?.paid !== undefined) {
      results = results.filter((order) => order.paid === filters.paid);
    }

    const total = results.length;

    // Apply pagination
    const limit = filters?.limit ?? 10;
    const offset = filters?.offset ?? 0;
    results = results.slice(offset, offset + limit);

    return { orders: results, total };
  }

  static updateOrder(id: string, updates: UpdateOrderInput): Order | undefined {
    const order = store.getById(id);
    if (!order) return undefined;

    // BUG-3: Enforce valid status transitions
    if (updates.status) {
      if (!isValidStatusTransition(order.status, updates.status)) {
        // Do not update status if transition is invalid
        // (other updates like deliveryAddress can still proceed, but status stays unchanged)
        delete updates.status;
      } else {
        order.status = updates.status;
      }
    }

    if (updates.deliveryAddress) {
      order.deliveryAddress = updates.deliveryAddress;
    }

    if (updates.orderedItems) {
      order.orderedItems = updates.orderedItems;
    }

    return store.update(id, order);
  }

  static updateStatus(id: string, newStatus: OrderStatus): Order | undefined {
    const order = store.getById(id);
    if (!order) return undefined;

    // BUG-3: Enforce valid status transitions
    if (!isValidStatusTransition(order.status, newStatus)) {
      // Return unchanged order (do not update status)
      return order;
    }

    order.status = newStatus;
    return store.update(id, order);
  }

  static updatePayment(id: string, paymentId: string): Order | undefined {
    const order = store.getById(id);
    if (!order) return undefined;

    order.paid = true;
    order.paymentId = paymentId;
    return store.update(id, order);
  }

  static markDelivered(id: string): Order | undefined {
    const order = store.getById(id);
    if (!order) return undefined;

    order.deliveredAt = new Date().toISOString();
    order.status = OrderStatus.Sent;
    return store.update(id, order);
  }

  static deleteOrder(id: string): boolean {
    return store.delete(id);
  }
}

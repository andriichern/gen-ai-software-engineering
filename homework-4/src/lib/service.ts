import { Order, OrderStatus, UpdateOrderInput } from "./types";
import store from "./store";

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

export class OrderService {
  static createOrder(customerId: string, orderedItems: string[], deliveryAddress: string): Order {
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

    // BUG-4: Status filter has loose comparison / incorrect logic
    // Current: uses loose equality (==) and string search which can match partial strings
    // e.g., filtering for "In" would match "In Delivery" and "New" due to poor logic
    if (filters?.status) {
      results = results.filter((order) => order.status == filters.status);
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

    // BUG-3: No status transition validation
    // Should prevent invalid state transitions (e.g., Sent -> Processing, Sent -> New)
    // Currently: allows any transition from any state to any state
    if (updates.status) {
      order.status = updates.status;
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

    // BUG-3: Same issue - no status transition validation
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

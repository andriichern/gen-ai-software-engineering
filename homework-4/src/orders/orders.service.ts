import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { Order, OrderStatus } from '@/lib/types';
import { OrderService as LibOrderService } from '@/lib/service';
import { validateCreateOrder, validateUpdatePayment, validateStatusUpdate } from '@/lib/validator';

@Injectable()
export class OrdersService {
  create(data: {
    customerId: string;
    orderedItems: string[];
    deliveryAddress: string;
  }): Order {
    const validation = validateCreateOrder(data);
    if (!validation.valid) {
      throw new BadRequestException({
        error: 'VALIDATION_ERROR',
        message: 'Invalid order data',
        details: validation.errors,
      });
    }

    return LibOrderService.createOrder(
      data.customerId,
      data.orderedItems,
      data.deliveryAddress,
    );
  }

  list(filters?: {
    status?: string;
    customerId?: string;
    paid?: boolean;
    limit?: number;
    offset?: number;
  }) {
    return LibOrderService.listOrders(filters as any);
  }

  getById(id: string): Order | undefined {
    const order = LibOrderService.getOrderById(id);
    if (!order) {
      throw new NotFoundException('Order not found');
    }
    return order;
  }

  delete(id: string) {
    const deleted = LibOrderService.deleteOrder(id);
    if (!deleted) {
      throw new NotFoundException('Order not found');
    }
    return { message: 'Order deleted successfully' };
  }

  updateStatus(id: string, status: OrderStatus): Order | undefined {
    const validation = validateStatusUpdate(status);
    if (!validation.valid) {
      throw new BadRequestException(validation.error);
    }

    const order = LibOrderService.updateStatus(id, status);
    if (!order) {
      throw new NotFoundException('Order not found');
    }
    return order;
  }

  updatePayment(id: string, paymentId: string): Order | undefined {
    const validation = validateUpdatePayment({ paymentId });
    if (!validation.valid) {
      throw new BadRequestException({
        error: 'VALIDATION_ERROR',
        message: 'Invalid payment data',
        details: validation.errors,
      });
    }

    const order = LibOrderService.updatePayment(id, paymentId);
    if (!order) {
      throw new NotFoundException('Order not found');
    }
    return order;
  }

  markDelivered(id: string): Order | undefined {
    const order = LibOrderService.markDelivered(id);
    if (!order) {
      throw new NotFoundException('Order not found');
    }
    return order;
  }
}

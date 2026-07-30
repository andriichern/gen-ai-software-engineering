import {
  Controller,
  Get,
  Post,
  Patch,
  Delete,
  Param,
  Body,
  Query,
  HttpStatus,
  HttpCode,
} from '@nestjs/common';
import { OrdersService } from './orders.service';
import { Order, OrderStatus } from '@/lib/types';

@Controller('api/orders')
export class OrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  @Post()
  @HttpCode(HttpStatus.CREATED)
  create(
    @Body()
    createOrderDto: {
      customerId: string;
      orderedItems: string[];
      deliveryAddress: string;
    },
  ): Order {
    return this.ordersService.create(createOrderDto);
  }

  @Get()
  list(
    @Query('status') status?: string,
    @Query('customerId') customerId?: string,
    @Query('paid') paid?: string,
    @Query('limit') limit?: string,
    @Query('offset') offset?: string,
  ) {
    return this.ordersService.list({
      status,
      customerId,
      paid: paid ? paid === 'true' : undefined,
      limit: limit ? parseInt(limit) : undefined,
      offset: offset ? parseInt(offset) : undefined,
    });
  }

  @Get(':id')
  getById(@Param('id') id: string): Order | undefined {
    return this.ordersService.getById(id);
  }

  @Delete(':id')
  delete(@Param('id') id: string) {
    return this.ordersService.delete(id);
  }

  @Patch(':id/status')
  updateStatus(
    @Param('id') id: string,
    @Body() body: { status: OrderStatus },
  ): Order | undefined {
    return this.ordersService.updateStatus(id, body.status);
  }

  @Patch(':id/payment')
  updatePayment(
    @Param('id') id: string,
    @Body() body: { paymentId: string },
  ): Order | undefined {
    return this.ordersService.updatePayment(id, body.paymentId);
  }

  @Patch(':id/delivery')
  markDelivered(@Param('id') id: string): Order | undefined {
    return this.ordersService.markDelivered(id);
  }
}

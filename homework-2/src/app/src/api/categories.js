import { request } from "./client.js";

export function listCategories() {
  return request("/category/list");
}

export function getCategory(key) {
  return request(`/category/${key}`);
}

export function createCategory(key, keywords = []) {
  return request("/category", { method: "POST", json: { key, keywords } });
}

export function addCategoryKeywords(key, keywords) {
  return request(`/category/${key}`, { method: "PUT", json: { keywords } });
}

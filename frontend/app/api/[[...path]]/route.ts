import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

async function handleProxy(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  const { path } = await context.params;
  const backendBase = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
  const subPath = path && path.length > 0 ? path.join('/') : '';
  const search = request.nextUrl.search || '';
  const targetUrl = `${backendBase}/api${subPath ? '/' + subPath : ''}${search}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower !== 'host' && lower !== 'content-length') {
      headers.set(key, value);
    }
  });

  try {
    const body =
      request.method !== 'GET' && request.method !== 'HEAD'
        ? await request.arrayBuffer()
        : undefined;

    const res = await fetch(targetUrl, {
      method: request.method,
      headers,
      body,
      // @ts-ignore
      duplex: 'half',
    });

    const responseHeaders = new Headers();
    res.headers.forEach((value, key) => {
      responseHeaders.set(key, value);
    });

    return new NextResponse(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: responseHeaders,
    });
  } catch (error: any) {
    console.error(`[API Proxy Error] Failed to proxy to ${targetUrl}:`, error.message);
    return NextResponse.json(
      {
        error: `Failed to connect to backend at ${targetUrl}`,
        detail: error.message,
        backend_url: backendBase,
      },
      { status: 502 }
    );
  }
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path?: string[] }> }) {
  return handleProxy(req, ctx);
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path?: string[] }> }) {
  return handleProxy(req, ctx);
}

export async function PUT(req: NextRequest, ctx: { params: Promise<{ path?: string[] }> }) {
  return handleProxy(req, ctx);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ path?: string[] }> }) {
  return handleProxy(req, ctx);
}

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ path?: string[] }> }) {
  return handleProxy(req, ctx);
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
      'Access-Control-Allow-Headers': '*',
    },
  });
}

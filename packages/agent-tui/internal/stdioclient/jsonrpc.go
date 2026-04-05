package stdioclient

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync/atomic"
)

// JSON-RPC 2.0 wire types.

// Request is a JSON-RPC 2.0 request.
type Request struct {
	JSONRPC string      `json:"jsonrpc"`
	Method  string      `json:"method"`
	Params  interface{} `json:"params,omitempty"`
	ID      int64       `json:"id"`
}

// Response is a JSON-RPC 2.0 response.
type Response struct {
	JSONRPC string          `json:"jsonrpc"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
	ID      *int64          `json:"id,omitempty"`
}

// RPCError is a JSON-RPC 2.0 error object.
type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func (e *RPCError) Error() string {
	return fmt.Sprintf("JSON-RPC error %d: %s", e.Code, e.Message)
}

// Notification is a JSON-RPC 2.0 notification (no id).
type Notification struct {
	JSONRPC string          `json:"jsonrpc"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// StreamEventParams is the params for a stream.event notification.
type StreamEventParams struct {
	Type string          `json:"type"`
	Data json.RawMessage `json:"data"`
}

// rawMessage is used for initial JSON parsing to determine message type.
type rawMessage struct {
	JSONRPC string          `json:"jsonrpc"`
	Method  string          `json:"method,omitempty"`
	ID      *int64          `json:"id,omitempty"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// Writer writes JSON-RPC objects as newline-delimited JSON.
type Writer struct {
	w  io.Writer
	id atomic.Int64
}

// NewWriter creates a JSON-RPC writer.
func NewWriter(w io.Writer) *Writer {
	return &Writer{w: w}
}

// WriteRequest sends a JSON-RPC request and returns the request ID.
func (w *Writer) WriteRequest(method string, params interface{}) (int64, error) {
	id := w.id.Add(1)
	req := Request{
		JSONRPC: "2.0",
		Method:  method,
		Params:  params,
		ID:      id,
	}
	data, err := json.Marshal(req)
	if err != nil {
		return 0, err
	}
	data = append(data, '\n')
	_, err = w.w.Write(data)
	return id, err
}

// Reader reads JSON-RPC messages from a line-delimited stream.
type Reader struct {
	scanner *bufio.Scanner
}

// NewReader creates a JSON-RPC reader.
func NewReader(r io.Reader) *Reader {
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 0, 1024*1024), 1024*1024) // 1MB buffer
	return &Reader{scanner: scanner}
}

// ReadMessage reads the next JSON-RPC message.
// Returns either a Response (has ID) or a Notification (no ID).
// Returns io.EOF when the stream ends.
func (r *Reader) ReadMessage() (*Response, *Notification, error) {
	if !r.scanner.Scan() {
		if err := r.scanner.Err(); err != nil {
			return nil, nil, err
		}
		return nil, nil, io.EOF
	}

	line := r.scanner.Bytes()
	if len(line) == 0 {
		return r.ReadMessage() // skip empty lines
	}

	var raw rawMessage
	if err := json.Unmarshal(line, &raw); err != nil {
		return nil, nil, fmt.Errorf("invalid JSON-RPC message: %w", err)
	}

	if raw.ID != nil {
		// It's a response
		return &Response{
			JSONRPC: raw.JSONRPC,
			Result:  raw.Result,
			Error:   raw.Error,
			ID:      raw.ID,
		}, nil, nil
	}

	// It's a notification
	return nil, &Notification{
		JSONRPC: raw.JSONRPC,
		Method:  raw.Method,
		Params:  raw.Params,
	}, nil
}

// MethodNotFound is the JSON-RPC error code for "Method not found".
const MethodNotFound = -32601

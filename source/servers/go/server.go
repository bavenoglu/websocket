package main

import (
	"bufio"
	"encoding/binary"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
)

var (
	upgrader = websocket.Upgrader{
		ReadBufferSize:    72000,
		WriteBufferSize:   72000,
		EnableCompression: false,
		CheckOrigin:       func(r *http.Request) bool { return true },
	}
)

type ServerLog struct {
	TestID    uint16
	ClientID  uint16
	MsgIndex  uint32
	Status    string
	ProcessMs float64
}

var logChan = make(chan ServerLog, 1_000_000)

func main() {

	// Go runtime parallelism; NOT a worker count.
    runtime.GOMAXPROCS(4)

	var port int
	var testID string
	flag.IntVar(&port, "port", 8000, "listen port")
	flag.StringVar(&testID, "test-id", "1", "test id")
	flag.Parse()

	logFileName := fmt.Sprintf("server_log_%s.csv", testID)
	f, err := os.Create("/logs/" + logFileName)
	if err != nil {
		log.Fatal(err)
	}

	writer := bufio.NewWriterSize(f, 4*1024*1024)
	writer.WriteString("test_id,conn_id,index,status,process_ms\n")

	go serverLogWriter(writer, f)

	http.HandleFunc("/ws", wsHandler)

	srv := &http.Server{
		Addr: fmt.Sprintf("0.0.0.0:%d", port),
	}

	go func() {
		log.Printf("WebSocket echo server listening on :%d", port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal(err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)

	<-stop
	log.Println("Server stopping..")
	srv.Close()

	for len(logChan) > 0 {
		log.Printf("Log queue: %d", len(logChan))
		time.Sleep(500 * time.Millisecond)
	}

	close(logChan)
	time.Sleep(1 * time.Second)
}

func wsHandler(w http.ResponseWriter, r *http.Request) {
	c, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}

	defer c.Close()
	// TCP_NODELAY
	if tcp, ok := c.UnderlyingConn().(*net.TCPConn); ok {
		if err := tcp.SetNoDelay(true); err != nil {
			log.Println(err)
		}
	}
	c.SetReadLimit(72000)

	for {
		mt, message, err := c.ReadMessage()
		if err != nil {
			return
		}

		start := time.Now()

		var tid, cid uint16
		var seq uint32
		if len(message) >= 8 {
			tid = binary.BigEndian.Uint16(message[0:2])
			cid = binary.BigEndian.Uint16(message[2:4])
			seq = binary.BigEndian.Uint32(message[4:8])
		}

		err = c.WriteMessage(mt, message)

		status := "OK"
		if err != nil {
			status = "FAIL"
		}

		processMs := float64(time.Since(start).Nanoseconds()) / 1e6

		if seq >= 5 {
			logChan <- ServerLog{
				TestID:    tid,
				ClientID:  cid,
				MsgIndex:  seq,
				Status:    status,
				ProcessMs: processMs,
			}
		}

		if err != nil {
			return
		}
	}
}

func serverLogWriter(w *bufio.Writer, f *os.File) {
	buffer := make([]ServerLog, 0, 100_000)

	flush := func() {
		for _, l := range buffer {
			fmt.Fprintf(w, "%d,%d,%d,%s,%.6f\n",
				l.TestID,
				l.ClientID,
				l.MsgIndex,
				l.Status,
				l.ProcessMs,
			)
		}
		w.Flush()
		buffer = buffer[:0]
	}

	for l := range logChan {
		buffer = append(buffer, l)
		if len(buffer) >= 100_000 {
			flush()
		}
	}

	if len(buffer) > 0 {
		flush()
	}

	w.Flush()
	f.Sync()
	f.Close()
}

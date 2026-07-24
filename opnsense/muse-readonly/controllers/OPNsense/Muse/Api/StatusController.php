<?php

/*
 * Minimal read-only telemetry endpoint for Home Assistant.
 * This controller intentionally exposes no mutable action.
 */

namespace OPNsense\Muse\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;

class StatusController extends ApiControllerBase
{
    public function gatewaysAction()
    {
        if (!$this->request->isGet()) {
            $this->response->setStatusCode(405, "Method Not Allowed");
            return ["status" => "method_not_allowed"];
        }

        $raw = json_decode((new Backend())->configdRun('interface gateways status'), true);
        if (!is_array($raw)) {
            $this->response->setStatusCode(503, "Service Unavailable");
            return ["status" => "unavailable", "gateways" => []];
        }

        $gateways = [];
        foreach ($raw as $item) {
            $gateways[] = [
                "name" => (string)($item["name"] ?? ""),
                "address" => (string)($item["address"] ?? ""),
                "status" => (string)($item["status"] ?? ""),
                "status_translated" => (string)($item["status_translated"] ?? ""),
                "loss" => (string)($item["loss"] ?? ""),
                "delay" => (string)($item["delay"] ?? ""),
                "stddev" => (string)($item["stddev"] ?? ""),
                "monitor" => (string)($item["monitor"] ?? ""),
            ];
        }

        return [
            "status" => "ok",
            "generated_at" => gmdate("c"),
            "gateways" => $gateways,
        ];
    }
}
